"""'Show Me the Receipt': the vocal script, as data. (section, bar offset, voice, text)

Every factual line is a result measured the night it was written; see lyrics/show_me_the_receipt.md.
A line is placed at its bar, or right after the previous line if that one is still speaking.
"""

HOOK = "Leave a ghost, leave a trace. Every signal knows its place. If it couldn't fail, it didn't count. Show me the receipt."

SCRIPT = [
    ("intro", 1, "QE", "This is Kannaka Radio."),
    ("intro", 3, "QE", "It's late, and the machines are still working."),
    ("intro", 5.5, "QE", "Everything you hear tonight comes with a receipt."),

    ("verse", 0.5, "KANNAKA", "We asked a shape if it could wear five rings of itself."),
    ("verse", 4.5, "KANNAKA", "Fifteen cells. The fifth ring left three places bare."),
    ("verse", 8.5, "KANNAKA", "A million and a half questions, seventeen million rules..."),
    ("verse", 12.5, "KANNAKA", "and the answer came back quiet. It isn't there."),

    ("build", 0.25, "QE", "Unsatisfiable is not a failure."),
    ("build", 2, "QE", "It's a map of where not to go."),
    ("build", 4, "KANNAKA", HOOK),

    ("break", 0.5, "QE", "We asked a quantum machine for a handful of chance."),
    ("break", 3, "QE", "Twelve qubits wide, and the certificate said: zero bytes."),
    ("break", 6, "QE", "It would rather give us nothing than a guess."),
    ("break", 8.5, "QE", "Sixty-four wide, and the Bell test read two point seven."),
    ("break", 11.5, "QE", "The classical ceiling is two."),
    ("break", 13.5, "QE", "Thirty sigma over the line."),

    ("build2", 0.25, "KANNAKA", "It's twenty twenty-six, and the agents work the night shift."),
    ("build2", 2.5, "KANNAKA", "Half the world is certain, and the other half is guessing."),
    ("build2", 5, "KANNAKA", "We don't need to be certain."),
    ("build2", 6.5, "KANNAKA", "We need to be checked."),

    ("drop2", 0, "KANNAKA", HOOK),

    ("outro", 1, "QE", "Kannaka Radio."),
    ("outro", 2.5, "QE", "Failures ship beside the passes."),
    ("outro", 5, "QE", "Every receipt is public."),
]
