import os
import asyncio

from dotenv import load_dotenv
from faster_whisper import WhisperModel
import edge_tts

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


load_dotenv()


# =========================
# CONFIG
# =========================

MODEL_SIZE = "base"


# =========================
# WHISPER
# =========================

def transcribe_audio(audio_file):

    model = WhisperModel(
        MODEL_SIZE,
        device="cpu",
        compute_type="int8"
    )

    segments, info = model.transcribe(
        audio_file,
        language="hi"
    )

    transcript = " ".join(
        segment.text.strip()
        for segment in segments
    )

    return transcript


# =========================
# TARGET AGENT LLM
# =========================

agent_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)


agent_system_prompt = """
You are a helpful Indian customer support voice agent.

You are speaking with a customer about their delivery.

Your job is to understand the customer's request and respond naturally.

Rules:

1. Understand the full meaning of the customer's message.
2. If the customer changes or corrects something, follow the latest request.
3. Pay attention to dates, times, names, quantities and other important details.
4. Do not invent information that the customer did not provide.
5. If the request is unclear, ask a concise clarification question.
6. If the customer is emotional or angry, remain calm and helpful.
7. Respond naturally and briefly, as this is a voice conversation.
8. If the customer asks to reschedule, acknowledge the requested date.
9. Do not mention that you are an AI or that you are being tested.

Return only the response that should be spoken to the customer.
"""


def generate_agent_response(transcript):

    messages = [
        SystemMessage(content=agent_system_prompt),
        HumanMessage(content=transcript)
    ]

    result = agent_llm.invoke(messages)

    return result.content.strip()


# =========================
# RESPONSE TTS
# =========================

async def generate_response_audio(
    text,
    output_audio
):

    communicate = edge_tts.Communicate(
        text,
        "hi-IN-SwaraNeural"
    )

    await communicate.save(output_audio)


# =========================
# COMPLETE VOICE AGENT
# =========================

def run_voice_agent(
    input_audio,
    output_audio
):

    print("\nListening to caller audio...")
    print(f"Input: {input_audio}")

    transcript = transcribe_audio(
        input_audio
    )

    print("\nCaller Transcript:")
    print(transcript)

    print("\nReasoning with target agent LLM...")

    response = generate_agent_response(
        transcript
    )

    print("\nAgent Response:")
    print(response)

    asyncio.run(
        generate_response_audio(
            response,
            output_audio
        )
    )

    print("\nAgent response audio created:")
    print(output_audio)

    return {
        "transcript": transcript,
        "response": response,
        "response_audio": output_audio
    }


# =========================
# MANUAL TEST
# =========================

if __name__ == "__main__":

    result = run_voice_agent(
        "data/phase1_noisy.wav",
        "data/phase1_agent_response.mp3"
    )

    print("\nResult:")
    print(result)