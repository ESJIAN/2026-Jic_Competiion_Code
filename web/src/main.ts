export {};

interface Config {
    left_scale: number;
    right_scale: number;
}

type StatusType = 'info' | 'success' | 'error';
type ControlAction = 'move_forward' | 'move_backward' | 'rotate_cw' | 'rotate_ccw' | 'stop';

interface LidarData {
    ranges?: number[];
    angle_min?: number;
    angle_max?: number;
    range_min?: number;
    range_max?: number;
}

class DOMBuilder {
    static el<K extends keyof HTMLElementTagNameMap>(
        tag: K,
        classes: string = '',
        children: Array<HTMLElement | string> = [],
        props: Record<string, unknown> = {},
    ): HTMLElementTagNameMap[K] {
        const element = document.createElement(tag);
        if (classes) {
            element.className = classes;
        }

        children.forEach((child) => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child) {
                element.appendChild(child);
            }
        });

        Object.entries(props).forEach(([key, value]) => {
            if (key === 'dataset' && value && typeof value === 'object') {
                Object.entries(value as Record<string, string>).forEach(([k, v]) => {
                    element.dataset[k] = v;
                });
            } else {
                (element as unknown as Record<string, unknown>)[key] = value;
            }
        });

        return element;
    }
}

class App {
    private readonly API_BASE = '/api';
    private appRoot: HTMLElement;

    private currentConfig: Config = {
        left_scale: 1.0,
        right_scale: 1.0,
    };

    private pollTimers: number[] = [];
    private statusTimer: number | null = null;
    private activeKey: string | null = null;

    private leftScaleInput!: HTMLInputElement;
    private rightScaleInput!: HTMLInputElement;
    private leftValDisplay!: HTMLElement;
    private rightValDisplay!: HTMLElement;
    private saveBtn!: HTMLButtonElement;

    private linearSpeedInput!: HTMLInputElement;
    private angularSpeedInput!: HTMLInputElement;
    private linearSpeedDisplay!: HTMLElement;
    private angularSpeedDisplay!: HTMLElement;

    private fwdBtn!: HTMLButtonElement;
    private bwdBtn!: HTMLButtonElement;
    private cwBtn!: HTMLButtonElement;
    private ccwBtn!: HTMLButtonElement;
    private stopBtn!: HTMLButtonElement;

    private batteryVoltageDisplay!: HTMLElement;
    private batteryStatusText!: HTMLElement;
    private batteryLevelBar!: HTMLElement;
    private leftSpeedDisplay!: HTMLElement;
    private rightSpeedDisplay!: HTMLElement;

    private imuConnEl!: HTMLElement;
    private imuTimeEl!: HTMLElement;
    private imuCalibEl!: HTMLElement;
    private imuOrientEl!: HTMLElement;
    private imuGyroEl!: HTMLElement;
    private imuAccelEl!: HTMLElement;

    private lidarCanvas!: HTMLCanvasElement;
    private lidarCtx!: CanvasRenderingContext2D | null;
    private lidarStateEl!: HTMLElement;

    private cameraFrame!: HTMLImageElement;
    private cameraStatusEl!: HTMLElement;

    private statusDiv!: HTMLElement;

    constructor() {
        const root = document.getElementById('app');
        if (!root) {
            throw new Error('Root element #app not found');
        }
        this.appRoot = root;

        this.render();
        this.init();
    }

    private render(): void {
        this.appRoot.innerHTML = '';

        const shell = DOMBuilder.el('div', 'min-h-screen text-slate-100', [
            DOMBuilder.el('div', 'mx-auto max-w-7xl px-3 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-10', [
                DOMBuilder.el('div', 'rounded-[1.5rem] border border-white/10 bg-slate-950/90 shadow-2xl shadow-slate-950/40 backdrop-blur overflow-hidden sm:rounded-[2rem]', [
                    this.buildHero(),
                    this.buildQuickNav(),
                    DOMBuilder.el('main', 'space-y-6 bg-slate-50 px-3 py-4 text-slate-900 sm:px-6 sm:py-6 lg:px-8 lg:py-8', [
                        this.buildChassisSection(),
                        this.buildIMUSection(),
                        this.buildLidarSection(),
                        this.buildCameraSection(),
                        this.buildFooterStatus(),
                    ]),
                ]),
            ]),
        ]);

        this.appRoot.appendChild(shell);
    }

    private buildHero(): HTMLElement {
        return DOMBuilder.el('header', 'relative overflow-hidden bg-slate-950 px-4 py-5 text-white sm:px-8 sm:py-8', [
            DOMBuilder.el('div', 'relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between', [
                DOMBuilder.el('div', 'space-y-2', [
                    DOMBuilder.el('div', 'inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-[11px] font-semibold tracking-[0.24em] text-cyan-200 uppercase', [
                        'Robot Control Panel',
                    ]),
                    DOMBuilder.el('h1', 'text-2xl font-bold tracking-tight sm:text-3xl lg:text-4xl', [
                        'One-page chassis, IMU, LiDAR, and camera dashboard',
                    ]),
                    DOMBuilder.el('p', 'max-w-3xl text-sm leading-6 text-slate-300 sm:text-base', [
                        'Four original tabs are merged into one responsive page. Desktop shows more data at once and mobile keeps each block easy to use.',
                    ]),
                ]),
                DOMBuilder.el('div', 'grid grid-cols-1 gap-2 sm:grid-cols-3 lg:min-w-[340px]', [
                    this.buildHeroBadge('Battery', '-- V', 'battery-hero-badge'),
                    this.buildHeroBadge('Left speed', '-- m/s', 'left-speed-hero-badge'),
                    this.buildHeroBadge('Right speed', '-- m/s', 'right-speed-hero-badge'),
                ]),
            ]),
        ]);
    }

    private buildHeroBadge(label: string, value: string, id: string): HTMLElement {
        const valueNode = DOMBuilder.el('div', 'text-lg font-semibold text-white sm:text-xl', [value], { id });
        return DOMBuilder.el('div', 'rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm', [
            DOMBuilder.el('div', 'text-[0.7rem] font-semibold uppercase tracking-[0.22em] text-slate-400', [label]),
            valueNode,
        ]);
    }

    private buildQuickNav(): HTMLElement {
        const links: Array<[string, string]> = [
            ['Chassis Tuning', '#chassis'],
            ['IMU Debug', '#imu'],
            ['LiDAR View', '#lidar'],
            ['Camera', '#camera'],
        ];

        return DOMBuilder.el('nav', 'border-t border-b border-white/10 bg-slate-900 px-3 py-3 sm:px-8', [
            DOMBuilder.el('div', 'grid grid-cols-2 gap-2 sm:flex sm:flex-wrap', links.map(([label, href]) => (
                DOMBuilder.el('a', 'inline-flex items-center justify-center rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-cyan-400 hover:text-white hover:shadow-lg hover:shadow-cyan-500/10', [label], {
                    href,
                })
            ))),
        ]);
    }

    private buildSectionShell(id: string, title: string, description: string, accent: { label: string; badge: string }, contentNode: HTMLElement): HTMLElement {
        return DOMBuilder.el('section', 'scroll-mt-6 rounded-3xl border border-slate-200 bg-white shadow-lg shadow-slate-200/70', [
            DOMBuilder.el('div', 'border-b border-slate-100 px-4 py-4 sm:px-6 sm:py-5', [
                DOMBuilder.el('div', 'flex flex-col gap-2', [
                    DOMBuilder.el('div', `inline-flex items-center self-start rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] ${accent.badge}`, [accent.label]),
                    DOMBuilder.el('h2', 'text-xl font-bold tracking-tight text-slate-900 sm:text-2xl', [title]),
                    DOMBuilder.el('p', 'max-w-4xl text-sm leading-6 text-slate-600 sm:text-base', [description]),
                ]),
            ]),
            DOMBuilder.el('div', 'px-4 py-4 sm:px-6 sm:py-6', [contentNode]),
        ], { id });
    }

    private buildChassisSection(): HTMLElement {
        this.batteryVoltageDisplay = DOMBuilder.el('div', 'text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl', ['-- V']);
        this.batteryStatusText = DOMBuilder.el('div', 'text-sm font-medium text-slate-500', ['Checking...']);
        this.batteryLevelBar = DOMBuilder.el('div', 'h-full w-full rounded-full bg-emerald-500 transition-all duration-500', []);

        const batteryIcon = DOMBuilder.el('div', 'relative flex h-9 w-20 items-center rounded-xl border-4 border-slate-600 p-1 sm:h-10 sm:w-24', [
            this.batteryLevelBar,
            DOMBuilder.el('div', 'absolute -right-3 top-1/2 h-4 w-2 -translate-y-1/2 rounded-r-sm bg-slate-600', []),
        ]);

        const batteryCard = DOMBuilder.el('div', 'rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm sm:p-5', [
            DOMBuilder.el('div', 'flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between', [
                DOMBuilder.el('div', 'space-y-1', [
                    DOMBuilder.el('h3', 'text-lg font-semibold text-slate-900', ['Battery Status']),
                    this.batteryStatusText,
                ]),
                DOMBuilder.el('div', 'flex items-center gap-4', [
                    this.batteryVoltageDisplay,
                    batteryIcon,
                ]),
            ]),
        ]);

        this.leftSpeedDisplay = DOMBuilder.el('div', 'text-2xl font-bold text-slate-900', ['-- m/s']);
        this.rightSpeedDisplay = DOMBuilder.el('div', 'text-2xl font-bold text-slate-900', ['-- m/s']);

        const speedCards = DOMBuilder.el('div', 'grid gap-4 sm:grid-cols-2', [
            DOMBuilder.el('div', 'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5', [
                DOMBuilder.el('div', 'text-sm font-medium text-slate-500', ['Left Wheel Speed']),
                this.leftSpeedDisplay,
            ]),
            DOMBuilder.el('div', 'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5', [
                DOMBuilder.el('div', 'text-sm font-medium text-slate-500', ['Right Wheel Speed']),
                this.rightSpeedDisplay,
            ]),
        ]);

        const layout = DOMBuilder.el('div', 'grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]', [
            DOMBuilder.el('div', 'space-y-6', [batteryCard, speedCards]),
            DOMBuilder.el('div', 'space-y-6', [this.buildSpeedCorrectionPanel(), this.buildMotionControlPanel()]),
        ]);

        return this.buildSectionShell(
            'chassis',
            'Chassis Tuning',
            'Live battery, wheel speed, and motor control stay visible in one place for faster tuning.',
            { label: 'Drive train', badge: 'bg-amber-50 text-amber-700' },
            layout,
        );
    }

    private buildSpeedCorrectionPanel(): HTMLElement {
        this.leftValDisplay = DOMBuilder.el('span', 'rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-mono font-semibold text-cyan-700', ['1.00']);
        this.leftScaleInput = DOMBuilder.el('input', 'w-full accent-cyan-600', [], {
            type: 'range', min: '0.5', max: '1.5', step: '0.01', value: '1.0',
        }) as HTMLInputElement;

        this.rightValDisplay = DOMBuilder.el('span', 'rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-mono font-semibold text-cyan-700', ['1.00']);
        this.rightScaleInput = DOMBuilder.el('input', 'w-full accent-cyan-600', [], {
            type: 'range', min: '0.5', max: '1.5', step: '0.01', value: '1.0',
        }) as HTMLInputElement;

        this.saveBtn = DOMBuilder.el('button', 'inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50', [
            'Save configuration',
        ]) as HTMLButtonElement;

        return DOMBuilder.el('div', 'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5', [
            DOMBuilder.el('div', 'mb-4 flex items-center justify-between', [
                DOMBuilder.el('h3', 'text-lg font-semibold text-slate-900', ['Speed Correction']),
                DOMBuilder.el('span', 'rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500', ['Fine tune']),
            ]),
            DOMBuilder.el('div', 'space-y-5', [
                DOMBuilder.el('div', 'space-y-2', [
                    DOMBuilder.el('div', 'flex items-center justify-between gap-3', [
                        DOMBuilder.el('label', 'text-sm font-medium text-slate-700', ['Left motor scale']),
                        this.leftValDisplay,
                    ]),
                    this.leftScaleInput,
                ]),
                DOMBuilder.el('div', 'space-y-2', [
                    DOMBuilder.el('div', 'flex items-center justify-between gap-3', [
                        DOMBuilder.el('label', 'text-sm font-medium text-slate-700', ['Right motor scale']),
                        this.rightValDisplay,
                    ]),
                    this.rightScaleInput,
                ]),
                DOMBuilder.el('div', 'pt-1', [this.saveBtn]),
            ]),
        ]);
    }

    private buildMotionControlPanel(): HTMLElement {
        this.linearSpeedDisplay = DOMBuilder.el('span', 'rounded-full bg-slate-100 px-2.5 py-1 text-xs font-mono font-semibold text-slate-700', ['0.50']);
        this.linearSpeedInput = DOMBuilder.el('input', 'w-full accent-cyan-600', [], {
            type: 'range', min: '0.1', max: '1.0', step: '0.05', value: '0.5',
        }) as HTMLInputElement;

        this.angularSpeedDisplay = DOMBuilder.el('span', 'rounded-full bg-slate-100 px-2.5 py-1 text-xs font-mono font-semibold text-slate-700', ['1.50']);
        this.angularSpeedInput = DOMBuilder.el('input', 'w-full accent-cyan-600', [], {
            type: 'range', min: '0.5', max: '3.0', step: '0.1', value: '1.5',
        }) as HTMLInputElement;

        this.fwdBtn = DOMBuilder.el('button', 'inline-flex min-h-11 items-center justify-center rounded-xl bg-cyan-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-cyan-700 active:scale-[0.99] touch-none', ['Forward']) as HTMLButtonElement;
        this.bwdBtn = DOMBuilder.el('button', 'inline-flex min-h-11 items-center justify-center rounded-xl bg-cyan-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-cyan-700 active:scale-[0.99] touch-none', ['Backward']) as HTMLButtonElement;
        this.cwBtn = DOMBuilder.el('button', 'inline-flex min-h-11 items-center justify-center rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 active:scale-[0.99] touch-none', ['Rotate CW']) as HTMLButtonElement;
        this.ccwBtn = DOMBuilder.el('button', 'inline-flex min-h-11 items-center justify-center rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 active:scale-[0.99] touch-none', ['Rotate CCW']) as HTMLButtonElement;
        this.stopBtn = DOMBuilder.el('button', 'inline-flex min-h-11 items-center justify-center rounded-xl bg-rose-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-rose-600 active:scale-[0.99] touch-none', ['STOP']) as HTMLButtonElement;

        return DOMBuilder.el('div', 'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5', [
            DOMBuilder.el('div', 'mb-4 flex items-center justify-between', [
                DOMBuilder.el('h3', 'text-lg font-semibold text-slate-900', ['Manual Control']),
                DOMBuilder.el('span', 'rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500', ['Hold or tap']),
            ]),
            DOMBuilder.el('div', 'space-y-5', [
                DOMBuilder.el('div', 'space-y-2', [
                    DOMBuilder.el('div', 'flex items-center justify-between gap-3', [
                        DOMBuilder.el('label', 'text-sm font-medium text-slate-700', ['Linear speed']),
                        this.linearSpeedDisplay,
                    ]),
                    this.linearSpeedInput,
                ]),
                DOMBuilder.el('div', 'space-y-2', [
                    DOMBuilder.el('div', 'flex items-center justify-between gap-3', [
                        DOMBuilder.el('label', 'text-sm font-medium text-slate-700', ['Angular speed']),
                        this.angularSpeedDisplay,
                    ]),
                    this.angularSpeedInput,
                ]),
                DOMBuilder.el('div', 'grid grid-cols-1 gap-3 sm:grid-cols-2', [
                    this.fwdBtn,
                    this.bwdBtn,
                    this.ccwBtn,
                    this.cwBtn,
                ]),
                DOMBuilder.el('div', 'pt-1', [this.stopBtn]),
            ]),
        ]);
    }

    private buildIMUSection(): HTMLElement {
        this.imuConnEl = DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', ['connection: --']);
        this.imuTimeEl = DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', ['timestamp: --']);
        this.imuCalibEl = DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', ['--']);
        this.imuOrientEl = DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', ['--']);
        this.imuGyroEl = DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', ['--']);
        this.imuAccelEl = DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', ['--']);

        const content = DOMBuilder.el('div', 'grid gap-4 md:grid-cols-2 xl:grid-cols-3', [
            this.buildDataCard('Status', this.imuConnEl, 'Connected state and sample timestamp.'),
            this.buildDataCard('Calibration', this.imuCalibEl, 'BNO055 calibration counters.'),
            this.buildDataCard('Orientation', this.imuOrientEl, 'Quaternion or pose-like values.'),
            this.buildDataCard('Angular velocity', this.imuGyroEl, 'Gyroscope values in rad/s.'),
            this.buildDataCard('Linear acceleration', this.imuAccelEl, 'Acceleration values in m/s2.'),
            this.buildDataCard('Time', this.imuTimeEl, 'Source timestamp converted to local time.'),
        ]);

        return this.buildSectionShell(
            'imu',
            'IMU Debug',
            'Inertial stream is visible without switching tabs.',
            { label: 'Inertial', badge: 'bg-cyan-50 text-cyan-700' },
            content,
        );
    }

    private buildLidarSection(): HTMLElement {
        this.lidarCanvas = DOMBuilder.el('canvas', 'w-full rounded-3xl border border-slate-200 bg-slate-950 shadow-2xl', [], {
            width: 720,
            height: 720,
        }) as HTMLCanvasElement;
        this.lidarCtx = this.lidarCanvas.getContext('2d');
        this.lidarStateEl = DOMBuilder.el('div', 'text-sm leading-6 text-slate-600', ['Waiting for scan data...']);

        const layout = DOMBuilder.el('div', 'grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]', [
            DOMBuilder.el('div', 'space-y-4', [
                DOMBuilder.el('div', 'flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500', [
                    DOMBuilder.el('span', 'rounded-full bg-slate-100 px-3 py-1', ['Top-down scan']),
                    DOMBuilder.el('span', 'rounded-full bg-slate-100 px-3 py-1', ['Center = robot']),
                    DOMBuilder.el('span', 'rounded-full bg-slate-100 px-3 py-1', ['Scale = 1 m / 100 px']),
                ]),
                this.lidarCanvas,
                this.lidarStateEl,
            ]),
            DOMBuilder.el('div', 'grid gap-4 sm:grid-cols-2 xl:grid-cols-1', [
                this.buildDataCard('Usage', DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', [
                    'range_min: --\nrange_max: --\nangle_min: --\nangle_max: --',
                ]), 'Raw range and angle ranges are summarized here.'),
                this.buildDataCard('Notes', DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', [
                    'Use this view to confirm returns, dead zones, and point cloud shape before tuning navigation.',
                ]), 'Optimized for desktop and mobile quick checks.'),
            ]),
        ]);

        return this.buildSectionShell(
            'lidar',
            'LiDAR View',
            'Scan geometry can be verified next to other signals on the same page.',
            { label: 'Laser scan', badge: 'bg-emerald-50 text-emerald-700' },
            layout,
        );
    }

    private buildCameraSection(): HTMLElement {
        this.cameraStatusEl = DOMBuilder.el('div', 'text-sm leading-6 text-slate-600', ['Streaming MJPEG feed from robot camera.']);
        const streamUrl = `${this.API_BASE}/camera/stream?t=${Date.now()}`;
        this.cameraFrame = DOMBuilder.el('img', 'w-full rounded-3xl border border-slate-200 bg-slate-950 object-contain shadow-2xl', [], {
            src: streamUrl,
            alt: 'Camera stream',
        }) as HTMLImageElement;
        this.cameraFrame.onerror = () => {
            this.cameraStatusEl.textContent = 'Camera stream failed to load. Check camera driver and network.';
        };

        const layout = DOMBuilder.el('div', 'grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]', [
            DOMBuilder.el('div', 'space-y-4', [this.cameraFrame, this.cameraStatusEl]),
            DOMBuilder.el('div', 'grid gap-4 sm:grid-cols-2 xl:grid-cols-1', [
                this.buildDataCard('Preview', DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', [
                    'Live feed is loaded once and kept open by the browser.\nUse it for exposure and framing checks.',
                ]), 'Stream updates continuously without refresh.'),
                this.buildDataCard('Mobile tip', DOMBuilder.el('div', 'whitespace-pre-line font-mono text-sm text-slate-700', [
                    'Rotate phone to landscape for wider view.\nFrame still fits page width.',
                ]), 'Layout automatically collapses to one column on narrow screens.'),
            ]),
        ]);

        return this.buildSectionShell(
            'camera',
            'Camera',
            'Camera preview stays in the same control surface.',
            { label: 'Vision', badge: 'bg-violet-50 text-violet-700' },
            layout,
        );
    }

    private buildDataCard(title: string, contentNode: HTMLElement, description: string): HTMLElement {
        return DOMBuilder.el('div', 'rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm', [
            DOMBuilder.el('div', 'mb-3 flex items-start justify-between gap-3', [
                DOMBuilder.el('h3', 'text-sm font-semibold uppercase tracking-[0.18em] text-slate-500', [title]),
                DOMBuilder.el('span', 'rounded-full bg-white px-2.5 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-slate-400', ['Live']),
            ]),
            contentNode,
            DOMBuilder.el('div', 'mt-3 text-xs leading-5 text-slate-500', [description]),
        ]);
    }

    private buildFooterStatus(): HTMLElement {
        this.statusDiv = DOMBuilder.el('div', 'rounded-2xl border border-slate-200 bg-slate-100 px-4 py-3 text-sm font-medium text-slate-700 shadow-lg shadow-slate-200/70 transition-opacity duration-300 opacity-0', ['Ready']);
        return DOMBuilder.el('footer', 'pt-2', [this.statusDiv]);
    }

    private init(): void {
        this.bindEvents();
        this.bindKeyboardControls();

        this.fetchChassisConfig();
        this.pollBattery();
        this.pollSpeed();
        this.pollIMU();
        this.pollLidar();

        this.pollTimers.push(window.setInterval(() => this.pollBattery(), 2000));
        this.pollTimers.push(window.setInterval(() => this.pollSpeed(), 250));
        this.pollTimers.push(window.setInterval(() => this.pollIMU(), 250));
        this.pollTimers.push(window.setInterval(() => this.pollLidar(), 500));
    }

    private bindEvents(): void {
        this.leftScaleInput.addEventListener('input', (event) => {
            this.leftValDisplay.textContent = parseFloat((event.target as HTMLInputElement).value).toFixed(2);
        });
        this.rightScaleInput.addEventListener('input', (event) => {
            this.rightValDisplay.textContent = parseFloat((event.target as HTMLInputElement).value).toFixed(2);
        });
        this.linearSpeedInput.addEventListener('input', (event) => {
            this.linearSpeedDisplay.textContent = parseFloat((event.target as HTMLInputElement).value).toFixed(2);
        });
        this.angularSpeedInput.addEventListener('input', (event) => {
            this.angularSpeedDisplay.textContent = parseFloat((event.target as HTMLInputElement).value).toFixed(2);
        });

        this.saveBtn.addEventListener('click', () => this.saveChassisConfig());

        this.bindPressHold(this.fwdBtn, 'move_forward');
        this.bindPressHold(this.bwdBtn, 'move_backward');
        this.bindPressHold(this.cwBtn, 'rotate_cw');
        this.bindPressHold(this.ccwBtn, 'rotate_ccw');
        this.stopBtn.addEventListener('click', () => this.sendControl('stop'));
    }

    private bindKeyboardControls(): void {
        const keyMap: Record<string, ControlAction> = {
            w: 'move_forward',
            s: 'move_backward',
            a: 'rotate_ccw',
            d: 'rotate_cw',
            arrowup: 'move_forward',
            arrowdown: 'move_backward',
            arrowleft: 'rotate_ccw',
            arrowright: 'rotate_cw',
        };

        document.addEventListener('keydown', (event) => {
            if (event.repeat) {
                return;
            }
            const activeTag = (event.target as HTMLElement | null)?.tagName;
            if (activeTag === 'INPUT' || activeTag === 'TEXTAREA') {
                return;
            }

            const key = event.key.toLowerCase();
            const action = keyMap[key];
            if (action && !this.activeKey) {
                this.activeKey = key;
                void this.sendControl(action);
            }
        });

        document.addEventListener('keyup', (event) => {
            const key = event.key.toLowerCase();
            if (key === this.activeKey) {
                this.activeKey = null;
                void this.sendControl('stop');
            }
        });
    }

    private bindPressHold(btn: HTMLButtonElement, action: ControlAction): void {
        const start = (): void => {
            void this.sendControl(action);
        };
        const end = (): void => {
            void this.sendControl('stop');
        };

        btn.addEventListener('pointerdown', (event) => {
            event.preventDefault();
            if (btn.setPointerCapture) {
                btn.setPointerCapture(event.pointerId);
            }
            start();
        });
        btn.addEventListener('pointerup', end);
        btn.addEventListener('pointercancel', end);
        btn.addEventListener('pointerleave', end);
    }

    private async fetchChassisConfig(): Promise<void> {
        try {
            const response = await fetch(`${this.API_BASE}/config`);
            if (!response.ok) {
                throw new Error('Failed to fetch config');
            }

            const data = await response.json() as Config;
            this.currentConfig = data;
            this.updateUI();
            this.showStatus('Configuration loaded', 'success');
        } catch (error) {
            this.showStatus(`Error loading config: ${String(error)}`, 'error');
        }
    }

    private updateUI(): void {
        this.leftScaleInput.value = this.currentConfig.left_scale.toString();
        this.rightScaleInput.value = this.currentConfig.right_scale.toString();
        this.leftValDisplay.textContent = this.currentConfig.left_scale.toFixed(2);
        this.rightValDisplay.textContent = this.currentConfig.right_scale.toFixed(2);
    }

    private async saveChassisConfig(): Promise<void> {
        const newConfig: Config = {
            left_scale: parseFloat(this.leftScaleInput.value),
            right_scale: parseFloat(this.rightScaleInput.value),
        };

        this.setLoading(true);

        try {
            const response = await fetch(`${this.API_BASE}/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConfig),
            });

            if (!response.ok) {
                throw new Error('Failed to save');
            }

            await response.json();
            this.currentConfig = newConfig;
            this.showStatus('Configuration saved successfully', 'success');
        } catch (error) {
            this.showStatus(`Error saving config: ${String(error)}`, 'error');
        } finally {
            this.setLoading(false);
        }
    }

    private async sendControl(action: ControlAction): Promise<void> {
        try {
            const payload: Record<string, unknown> = { action };
            if (this.linearSpeedInput) {
                payload.linear_speed = parseFloat(this.linearSpeedInput.value);
            }
            if (this.angularSpeedInput) {
                payload.angular_speed = parseFloat(this.angularSpeedInput.value);
            }

            const response = await fetch(`${this.API_BASE}/control`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error('Command failed');
            }

            if (action === 'stop') {
                this.showStatus('Stopped', 'info');
            } else {
                this.showStatus(`Running: ${action.replace('_', ' ').toUpperCase()}`, 'success');
            }
        } catch (error) {
            this.showStatus(`Error executing command: ${String(error)}`, 'error');
        }
    }

    private async pollBattery(): Promise<void> {
        try {
            const response = await fetch(`${this.API_BASE}/battery`);
            if (!response.ok) {
                throw new Error('Failed to fetch battery');
            }

            const data = await response.json() as { voltage?: number };
            const voltage = data.voltage;
            if (typeof voltage === 'number' && Number.isFinite(voltage)) {
                this.batteryVoltageDisplay.textContent = `${voltage.toFixed(2)} V`;
                const percentage = Math.max(0, Math.min(100, ((voltage - 10.0) / (12.6 - 10.0)) * 100));
                this.batteryLevelBar.style.width = `${percentage}%`;

                if (percentage < 20) {
                    this.batteryLevelBar.className = 'h-full rounded-full bg-rose-500 transition-all duration-500';
                    this.batteryStatusText.textContent = 'Low battery';
                    this.batteryStatusText.className = 'text-sm font-medium text-rose-600';
                    this.updateHeroBadge('battery-hero-badge', `${voltage.toFixed(2)} V`, 'text-rose-200');
                } else if (percentage < 50) {
                    this.batteryLevelBar.className = 'h-full rounded-full bg-amber-500 transition-all duration-500';
                    this.batteryStatusText.textContent = 'Medium';
                    this.batteryStatusText.className = 'text-sm font-medium text-amber-600';
                    this.updateHeroBadge('battery-hero-badge', `${voltage.toFixed(2)} V`, 'text-amber-200');
                } else {
                    this.batteryLevelBar.className = 'h-full rounded-full bg-emerald-500 transition-all duration-500';
                    this.batteryStatusText.textContent = 'Good';
                    this.batteryStatusText.className = 'text-sm font-medium text-emerald-600';
                    this.updateHeroBadge('battery-hero-badge', `${voltage.toFixed(2)} V`, 'text-white');
                }
            }
        } catch {
            this.batteryVoltageDisplay.textContent = '-- V';
            this.batteryStatusText.textContent = 'Error';
            this.batteryStatusText.className = 'text-sm font-medium text-rose-600';
            this.updateHeroBadge('battery-hero-badge', '-- V', 'text-slate-200');
        }
    }

    private async pollSpeed(): Promise<void> {
        try {
            const response = await fetch(`${this.API_BASE}/chassis/speed`);
            if (!response.ok) {
                throw new Error('Failed to fetch speed');
            }

            const data = await response.json() as { left_speed?: number; right_speed?: number };
            if (typeof data.left_speed === 'number') {
                this.leftSpeedDisplay.textContent = `${data.left_speed.toFixed(3)} m/s`;
                this.updateHeroBadge('left-speed-hero-badge', `${data.left_speed.toFixed(3)} m/s`, 'text-white');
            }
            if (typeof data.right_speed === 'number') {
                this.rightSpeedDisplay.textContent = `${data.right_speed.toFixed(3)} m/s`;
                this.updateHeroBadge('right-speed-hero-badge', `${data.right_speed.toFixed(3)} m/s`, 'text-white');
            }
        } catch {
            this.leftSpeedDisplay.textContent = '-- m/s';
            this.rightSpeedDisplay.textContent = '-- m/s';
            this.updateHeroBadge('left-speed-hero-badge', '-- m/s', 'text-slate-200');
            this.updateHeroBadge('right-speed-hero-badge', '-- m/s', 'text-slate-200');
        }
    }

    private async pollIMU(): Promise<void> {
        try {
            const response = await fetch(`${this.API_BASE}/imu`);
            if (!response.ok) {
                throw new Error('Failed to fetch IMU');
            }

            const data = await response.json() as Record<string, unknown>;
            const hasData = data && data.orientation && data.angular_velocity && data.linear_acceleration;

            this.imuConnEl.textContent = `connection: ${hasData ? 'connected' : 'disconnected'}`;
            if (typeof data.timestamp === 'number') {
                this.imuTimeEl.textContent = `timestamp: ${new Date(data.timestamp * 1000).toLocaleString()}`;
            } else {
                this.imuTimeEl.textContent = 'timestamp: --';
            }

            this.imuCalibEl.textContent = this.formatValue(data.calibration);
            this.imuOrientEl.textContent = this.formatValue(data.orientation);
            this.imuGyroEl.textContent = this.formatValue(data.angular_velocity);
            this.imuAccelEl.textContent = this.formatValue(data.linear_acceleration);
        } catch {
            this.imuConnEl.textContent = 'connection: disconnected';
            this.imuTimeEl.textContent = 'timestamp: --';
            this.imuCalibEl.textContent = '--';
            this.imuOrientEl.textContent = '--';
            this.imuGyroEl.textContent = '--';
            this.imuAccelEl.textContent = '--';
        }
    }

    private async pollLidar(): Promise<void> {
        try {
            const response = await fetch(`${this.API_BASE}/lidar`);
            if (!response.ok) {
                throw new Error('Failed to fetch LiDAR');
            }

            const data = await response.json() as LidarData;
            this.drawLidar(data);
        } catch {
            this.drawLidar(null);
        }
    }

    private drawLidar(data: LidarData | null): void {
        if (!this.lidarCtx || !this.lidarCanvas) {
            return;
        }

        const ctx = this.lidarCtx;
        const width = this.lidarCanvas.width;
        const height = this.lidarCanvas.height;
        const cx = width / 2;
        const cy = height / 2;
        const scale = Math.min(width, height) * 0.34;

        ctx.fillStyle = '#020617';
        ctx.fillRect(0, 0, width, height);

        ctx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = 0; i < width; i += width / 8) {
            ctx.moveTo(i, 0);
            ctx.lineTo(i, height);
            ctx.moveTo(0, i);
            ctx.lineTo(width, i);
        }
        ctx.stroke();

        ctx.strokeStyle = 'rgba(45, 212, 191, 0.22)';
        ctx.beginPath();
        ctx.arc(cx, cy, scale, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(cx, cy, scale * 0.5, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(cx, cy, 5, 0, Math.PI * 2);
        ctx.fill();

        const ranges = Array.isArray(data?.ranges) ? data.ranges : [];
        if (!ranges.length) {
            ctx.fillStyle = 'rgba(226, 232, 240, 0.9)';
            ctx.font = '600 20px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Waiting for scan...', cx, cy - 4);
            ctx.font = '400 14px sans-serif';
            ctx.fillText('LiDAR data is not available yet', cx, cy + 22);
            this.lidarStateEl.textContent = 'No scan data yet. Check the driver or wait for next frame.';
            return;
        }

        const angleMin = typeof data?.angle_min === 'number' ? data.angle_min : 0;
        const angleMax = typeof data?.angle_max === 'number' ? data.angle_max : Math.PI * 2;
        const rangeMin = typeof data?.range_min === 'number' ? data.range_min : 0;
        const rangeMax = typeof data?.range_max === 'number' ? data.range_max : 10;
        const angleIncrement = ranges.length > 1 ? (angleMax - angleMin) / ranges.length : 0;

        for (let index = 0; index < ranges.length; index += 1) {
            const dist = ranges[index];
            if (typeof dist !== 'number' || dist < rangeMin || dist > rangeMax) {
                continue;
            }

            const angle = angleMin + (index * angleIncrement);
            const x = cx + Math.cos(angle) * dist * scale;
            const y = cy - Math.sin(angle) * dist * scale;

            const alpha = Math.max(0.2, 1 - dist / rangeMax);
            ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
            ctx.fillRect(x, y, 2.5, 2.5);
        }

        this.lidarStateEl.textContent = `Samples: ${ranges.length} | range: ${rangeMin.toFixed(2)} - ${rangeMax.toFixed(2)} m`;
    }

    private formatValue(value: unknown, depth = 0): string {
        const indent = '  '.repeat(depth);

        if (value === null || value === undefined) {
            return `${indent}--`;
        }
        if (typeof value === 'number') {
            return `${indent}${Number.isFinite(value) ? value.toFixed(3) : '--'}`;
        }
        if (typeof value === 'string' || typeof value === 'boolean') {
            return `${indent}${String(value)}`;
        }
        if (Array.isArray(value)) {
            if (!value.length) {
                return `${indent}[]`;
            }
            return value.map((item) => this.formatValue(item, depth + 1)).join('\n');
        }
        if (typeof value === 'object') {
            const entries = Object.entries(value as Record<string, unknown>);
            if (!entries.length) {
                return `${indent}{}`;
            }
            return entries.map(([key, nestedValue]) => {
                const nested = this.formatValue(nestedValue, depth + 1);
                if (nested.includes('\n')) {
                    return `${indent}${key}:\n${nested}`;
                }
                return `${indent}${key}: ${nested.trimStart()}`;
            }).join('\n');
        }
        return `${indent}${String(value)}`;
    }

    private updateHeroBadge(id: string, value: string, textClass: string): void {
        const target = document.getElementById(id);
        if (!target) {
            return;
        }
        target.textContent = value;
        target.classList.remove('text-white', 'text-slate-200', 'text-amber-200', 'text-rose-200');
        target.classList.add(textClass);
    }

    private showStatus(message: string, type: StatusType = 'info'): void {
        if (!this.statusDiv) {
            return;
        }

        this.statusDiv.textContent = message;
        this.statusDiv.className = 'rounded-2xl border px-4 py-3 text-sm font-medium transition-opacity duration-300 opacity-100';

        if (type === 'success') {
            this.statusDiv.classList.add('border-emerald-200', 'bg-emerald-50', 'text-emerald-700');
        } else if (type === 'error') {
            this.statusDiv.classList.add('border-rose-200', 'bg-rose-50', 'text-rose-700');
        } else {
            this.statusDiv.classList.add('border-slate-200', 'bg-slate-100', 'text-slate-700');
        }

        if (this.statusTimer) {
            clearTimeout(this.statusTimer);
        }

        if (type !== 'error') {
            this.statusTimer = window.setTimeout(() => {
                this.statusDiv.classList.remove('opacity-100');
                this.statusDiv.classList.add('opacity-0');
            }, 3000);
        }
    }

    private setLoading(isLoading: boolean): void {
        if (!this.saveBtn) {
            return;
        }

        if (isLoading) {
            this.saveBtn.disabled = true;
            this.saveBtn.textContent = 'Saving...';
        } else {
            this.saveBtn.disabled = false;
            this.saveBtn.textContent = 'Save configuration';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new App();
});
