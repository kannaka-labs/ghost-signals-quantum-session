set -uo pipefail
JOB=$(pwd)
cd "$HOME/heesch-repo"
: > "$JOB/out.txt"
F=1
J="$JOB/joint_multi.py"; S=submission/best.heesch
say() { echo "$(date -u +%T) $*" | tee -a "$JOB/out.txt"; }
res() { grep -E "^(SAT|UNSAT|ENCODING)" | tail -1; }
rmax_and_D() {
  lo=339
  if python3 -u "$J" $S --free-from $F --r-only --decide 0/339 2>&1 | grep -q "^SAT"; then
    for r in $(seq 360 20 800); do
      if python3 -u "$J" $S --free-from $F --r-only --decide 0/$r 2>&1 | grep -q "^SAT"; then lo=$r; else break; fi
    done
    hi=$((lo + 20))
    while [ $((hi - lo)) -gt 1 ]; do
      mid=$(((lo + hi) / 2))
      if python3 -u "$J" $S --free-from $F --r-only --decide 0/$mid 2>&1 | grep -q "^SAT"; then lo=$mid; else hi=$mid; fi
    done
    say "RMAX = $lo"
  else
    lo=338; say "RMAX < 339 (R>=339 UNSAT, pockets allowed): every D>=4 impossible"
  fi
  D=4
  while :; do
    need=$(( (254 * D) / 3 + 1 ))
    [ $need -gt $lo ] && { say "D=$D needs |R| >= $need > RMAX: impossible, done"; break; }
    r=$(python3 -u "$J" $S --free-from $F --count-pockets --decide $D/$need --out "$JOB/beat_f1_D$D.heesch" 2>&1 | res)
    say "D=$D R>=$need: $r"
    D=$((D + 1))
  done
}
( r=$(python3 -u "$J" $S --free-from $F --count-pockets --decide 3/254 --out "$JOB/control_cp_f1.heesch" 2>&1 | res); say "control 3/254: $r" ) & A=$!
( r=$(python3 -u "$J" $S --free-from $F --count-pockets --decide 3/255 --out "$JOB/beat_f1_d3.heesch" 2>&1 | res); say "D<=3 R>=255: $r" ) & C=$!
# D<=2 first, then (in the same slot, so memory stays bounded) the ring-size search and the D>=4 checks
( r=$(python3 -u "$J" $S --free-from $F --count-pockets --decide 2/1 --out "$JOB/beat_f1_d2.heesch" 2>&1 | res); say "D<=2 any R: $r"; rmax_and_D ) & B=$!
( while sleep 900; do echo "$(date -u +%T) [mem] $(free -m | awk '/Mem/{print $3}') MB used" >> "$JOB/mem.txt"; done ) & M=$!
wait $A $B $C
kill $M
say "ALL DONE"