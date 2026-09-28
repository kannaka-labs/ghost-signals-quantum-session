set -uo pipefail
JOB=$(pwd)
REPO="$HOME/heesch-repo"
if [ ! -d "$REPO/.git" ]; then git clone --quiet --depth 1 https://github.com/Layr-Labs/heesch.git "$REPO"; fi
cd "$REPO"
python3 -m pip install --quiet --user -e . python-sat 2>&1 | tail -1
: > "$JOB/out.txt"
for s in hex13-kaplan-hc4hh4 hex15-kaplan-hc4hh4-a hex16-kaplan-hc4hh4; do
  echo "===== $s witness" | tee -a "$JOB/out.txt"
  python3 "$JOB/build_witness.py" --kaplan "$s" --m 4 --out "$JOB/$s.heesch" 2>&1 | tail -3 | tee -a "$JOB/out.txt"
  if [ -f "$JOB/$s.heesch" ]; then
    python3 -m heesch_verify "$JOB/$s.heesch" 2>&1 | grep -o '"hc_verified":[0-9]*' | tee -a "$JOB/out.txt"
    echo "----- $s joint ring 4/5 (count objective)" | tee -a "$JOB/out.txt"
    python3 "$JOB/joint_opt.py" "$JOB/$s.heesch" --max-cuts 5000 --out "$JOB/$s.joint.heesch" 2>&1 | grep -E 'OFFICIAL|no hole' | tee -a "$JOB/out.txt"
  fi
done