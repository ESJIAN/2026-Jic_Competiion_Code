#!/bin/bash

# Configuration
THRESHOLD=70.0
INTERVAL=1
# Processes to terminate (build tools vs compilers)
TARGETS=("colcon" "make" "ninja" "cmake" "cc1plus" "g++" "gcc" "ld" "c++")

echo "================================================="
echo " 🔥 RDK X5 Thermal Guard (Bash Edition)"
echo "    - Threshold: ${THRESHOLD}°C"
echo "    - Monitoring command: sudo hrut_somstatus"
echo "================================================="

while true; do
    # Get CPU temperature
    # Extract the line with "CPU", get the 3rd field.
    # Expected output line: "        CPU      : 56.4 (C)"
    CURRENT_TEMP=$(sudo hrut_somstatus 2>/dev/null | grep "CPU" | awk '{print $3}')
    
    # Check if we got a valid number
    if [[ -z "$CURRENT_TEMP" ]]; then
        echo "[Thermal Guard] ⚠️  Failed to read temperature."
        sleep $INTERVAL
        continue
    fi
    
    # Comparison using awk (returns 1 if true, 0 if false)
    IS_HOT=$(echo "$CURRENT_TEMP $THRESHOLD" | awk '{if ($1 > $2) print 1; else print 0}')

    if [ "$IS_HOT" -eq 1 ]; then
        echo ""
        echo "[Thermal Guard] ⚠️  CRITICAL TEMP: ${CURRENT_TEMP}°C > ${THRESHOLD}°C"
        echo "[Thermal Guard] 🛑  Terminating heavy processes..."
        
        for proc in "${TARGETS[@]}"; do
            # Use pkill. 
            # -f matches full command line (good for python scripts like colcon).
            # -x matches exact name (good for binaries).
            # We'll stick to simple pkill which matches process name by default, 
            # or pkill -f for things that might be scripts.
            pkill -f "$proc" > /dev/null 2>&1
        done
        
        echo "[Thermal Guard] ❄️  Cooldown mode active..."
        # Simple hysteresis: wait until temp drops below Threshold - 5
        while true; do
             sleep 2
             COOL_TEMP=$(sudo hrut_somstatus 2>/dev/null | grep "CPU" | awk '{print $3}')
             # Break if cooldown temp is empty or <= Threshold - 5
             IS_COOLED=$(echo "$COOL_TEMP $THRESHOLD" | awk '{if ($1 < ($2 - 5.0)) print 1; else print 0}')
             
             if [ "$IS_COOLED" -eq 1 ]; then
                echo "[Thermal Guard] ✅  Temperature stabilized (${COOL_TEMP}°C). Monitoring resumed."
                break
             fi
        done
    else
        # Optional: Print heartbeat or just stay silent
        # echo -ne "\rCurrent Temp: ${CURRENT_TEMP}°C  "
        :
    fi

    sleep $INTERVAL
done
