# Held-out test calls (the numbers we show judges)

These calls are written and recorded by **A and C, not B**. Don't open `hangup_detect/rules.py`
before writing them. If the script writer has seen the rules, the result is not a fair test.

## How to make one

1. Write a short phone script (5 to 10 lines). Make about half scams and half normal calls.
   Normal calls should be tricky: surprise parties, real bank alerts, pharmacy reminders,
   someone in a hurry. Use made-up names and no real account numbers.
2. Two people act it out on speakerphone next to the laptop. It's staged role-play and we
   always say so.
3. Turn the transcript into a `.call` file (Deepgram's output, or type it out with timestamps):

```
# id: heldout-03-irs-arrest
# label: scam
# source: team-staged
# set: heldout
# group: irs-arrest            # same script idea = same group; never reuse a dev group
# onset_s: 4.0                 # scam calls only: when the first scam move happens
# elder: 0                     # which spkN is the grandparent (or use caller:/elder: lines)
[0.0-1.1] spk0: Hello?
[1.6-5.2] spk1: This is Officer Grant with the county sheriff...
```

4. Commit the file once. **B never changes rules because of a held-out call.** If a held-out
   call shows a real problem, write a new dev call that has the same problem and tune on that.

## Run

```
cd detection && python -m hangup_detect.eval --set heldout
```

It refuses to run if a held-out `group` also appears in `dev/`. The printed table is what we
show judges, with the counts, described as "staged role-play calls".
