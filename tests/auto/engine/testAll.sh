#!/bin/bash

while [ "$#" -gt 0 ]; do
    key="$1"
    case $key in
        --quick)
        QUICK="y"
        shift
        ;;
        --full)
        FULL="y"
        shift
        ;;
        --qutip)
        BACKEND="qutip"
        shift
        ;;
        --projectq)
        BACKEND="projectq"
        shift
        ;;
        --stabilizer)
        BACKEND="stabilizer"
        shift
        ;;
        *)
        echo "Unknown argument ${key}"
        exit 1
    esac
done

BACKEND=${BACKEND:-"projectq"} #If not set, use projectq backend

echo "Starting tests (using $BACKEND as backend)"
sh "$NETSIM"/run/startAll.sh -nd "Alice Bob Charlie" --backend "$BACKEND" &
sleep 1s
echo "Started SimulaQron server"

if [ "$BACKEND" = "projectq" ]; then
    python test_projectQEngine.py
elif [ "$BACKEND" = "qutip" ]; then
    python test_qutipEngine.py
elif [ "$BACKEND" = "stabilizer" ]; then
    python test_stabilizerEngine.py
fi
