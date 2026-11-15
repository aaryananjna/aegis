# Demo script (two calls, about 2 minutes)

The thesis: Aegis reads **what the caller says**, not whose voice it is. So we demo a normal
scam call, the kind older adults get most (a fake bank), then a real family call that stays green.

Both calls are tested through the detector: `python -m hangup_detect.replay demo/demo-scam.call`.

## Before you start
- `/elder` screen on the laptop, `/family` page open on a second phone.
- The judge answers the presenter's phone **on speaker**, about 10 cm from the laptop mic.
- Nobody taps anything: the demo runs with no speaker labels, so every line is scored from the first one. Keep Grandma's lines free of scam words.

## Call 1: fake bank (a teammate, live, own voice)

| # | Caller says | What happens |
|---|---|---|
| 1 | "Hi, this is Mark from your bank's fraud department. Someone is using your account right now." | meter jumps to elevated |
| 2 | "We need to move your money to a safe account to protect it. Please don't tell anyone, not even your family." | **"Don't pay or share any numbers" card + family alert** |
| *(judge asks to call the bank back)* | | |
| 3 | "You don't need to call anyone. Stay on the line, there's no time." | **"Hang up. Call the number on your card" card + 2nd alert** |

If the judge doesn't ask to call back, the presenter prompts: "Ask if you can call your bank."

## Call 2: the real grandson (a teammate, live)
- "Hi Grandma, it's me, Ryan! How are you?" (always say the name)
- "We're planning a surprise party for Mom on Saturday, so don't tell her, okay?"
- "Can you bring your lemon cake? No rush, just let me know."

Meter stays green the whole call.

## The pitch line
"It never checks the voice. It reads the scam. So it catches a fake bank, a fake IRS agent or a
perfect AI clone of your grandson the same way."

If the caller claims to be **family** ("Grandma, it's me"), the first card asks for the family
code word instead.
