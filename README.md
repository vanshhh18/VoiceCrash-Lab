# VoiceCrashLab

**VoiceCrashLab** is an adversarial testing platform for AI voice
agents. It evaluates how well an agent handles realistic customer
conversations, especially when speech is unclear, noisy, emotional, or
changes during the call.

Instead of checking only whether an agent can respond, VoiceCrashLab
tests how reliably it understands the caller, follows the request, asks
for missing information, and recovers when a conversation becomes
difficult.

## Key Features

-   **Role-based scenario generation:** Generate customer-call scenarios
    based on the selected agent role, business type, and language.
-   **Noise robustness testing:** Test scenarios with traffic noise, fan
    noise, crowd noise, audio dropouts, and customer mumbling.
-   **LLM reasoning tests:** Challenge the agent with changing requests,
    ambiguous instructions, interruptions, multi-step queries, and
    emotional customer interactions.
-   **Voice-based testing:** Generate caller audio for test scenarios
    and evaluate the agent's spoken responses.
-   **Automated evaluation:** Use an OpenAI model as an evaluator to
    compare the agent's response with the expected behaviour.
-   **Failure analysis:** Identify issues such as intent
    misunderstanding and missing clarification, with failure details and
    suggested fixes.
-   **Results dashboard:** Review test outcomes and understand where the
    voice agent needs improvement.

## How It Works

1.  **Configure the agent:** Select the agent's role, business type, and
    language.
2.  **Generate scenarios:** VoiceCrashLab creates 10 test scenarios:
    -   5 easier scenarios focused on audio and noise robustness.
    -   5 harder scenarios focused on LLM reasoning and conversation
        handling.
3.  **Generate caller recordings:** **Gnani Timbre** generates the audio
    recordings for the customer scenarios.
4.  **Run the voice-agent test:** The generated caller audio is played
    to the AI voice agent, which processes the request and produces a
    spoken response.
5.  **Transcribe the agent response:** **Prisma** transcribes the
    agent's spoken response into text for evaluation.
6.  **Evaluate the response:** An **OpenAI model** acts as the judge. It
    checks the response against the expected behaviour and identifies
    whether the agent understood and handled the request correctly.
7.  **Review the results:** The dashboard displays pass/fail outcomes,
    failure categories, explanations, and suggested improvements.

## Technologies Used

  -----------------------------------------------------------------------
  Component               Tool / Technology       Purpose
  ----------------------- ----------------------- -----------------------
  Scenario audio          Gnani Timbre            Generates spoken caller
  generation                                      recordings

  Agent-response          Prisma                  Converts the agent's
  transcription                                   spoken response into
                                                  text

  AI evaluation           OpenAI model            Judges the agent
                                                  response against
                                                  expected behaviour

  Application logic       Python                  Runs the testing and
                                                  evaluation workflow

  Results interface       Dashboard               Displays test outcomes
                                                  and failure analysis
  -----------------------------------------------------------------------

> This table lists the tools used in the current project workflow. Add
> or update framework and infrastructure details to match the exact
> versions in your repository.

## Example Test Categories

### Noise and Audio Robustness

-   Traffic noise
-   Fan noise
-   Crowd noise
-   Audio dropouts
-   Mumbling or unclear speech

### LLM Reasoning and Conversation Handling

-   Changing customer requests
-   Ambiguous instructions
-   Interruptions and corrections
-   Multi-step customer queries
-   Emotional or frustrated callers

## Evaluation Output

For each test, VoiceCrashLab can present:

-   Caller input
-   Agent response
-   Expected behaviour
-   Pass/fail result
-   Failure category
-   Failure details
-   Suggested fix

Example failure categories include **Intent Misunderstanding** and
**Missing Clarification**.

## Demo Results

In the demonstrated run, the agent passed **20 out of 40 tests** and
failed **20**, resulting in a **50% pass rate**.

These figures describe that particular demo run; results may change
depending on the agent, scenarios, language, and audio conditions.

## Getting Started

The exact setup commands depend on the files and dependencies in your
repository.

1.  Clone the repository.
2.  Create and activate a Python virtual environment.
3.  Install the dependencies listed in `requirements.txt`, if present.
4.  Configure the required API credentials using environment variables.
5.  Run the application using the entry point provided in the
    repository.

Do not commit API keys or other secrets. Keep them in a local `.env`
file and add that file to `.gitignore`.

## Project Goal

VoiceCrashLab aims to help developers discover weaknesses in AI voice
agents before real customers encounter them. By combining realistic
voice scenarios, speech transcription, and AI-based evaluation, it makes
voice-agent testing more systematic and actionable.

------------------------------------------------------------------------

**VoiceCrashLab --- Don't just test whether AI works. Test how it
fails.**
