from audio.recorder import record_audio


scenarios = {
    1: "Mujhe apni delivery Monday ko chahiye.",
    2: "Bhai, meri delivery Monday ko reschedule kar sakte ho?",
    3: "Meri delivery Monday ko kar do.",
    4: "Actually meri delivery Monday ko... nahi, Tuesday ko kar do.",
    5: "Umm... woh... delivery... Monday...",
    6: "Delivery Monday ko chahiye. Actually nahi, Wednesday better hai.",
    7: "Hello, kya yahan Rahul bol raha hai?",
    8: "Teen baar delivery cancel ho chuki hai, mujhe abhi solution chahiye!"
}


for number, text in scenarios.items():

    print("\n" + "=" * 60)
    print(f"SCENARIO {number}")
    print(text)
    print("=" * 60)

    input("Press ENTER when you are ready to record...")

    output_file = f"data/scenario_{number}.wav"

    record_audio(output_file)

    print(f"Saved: {output_file}")