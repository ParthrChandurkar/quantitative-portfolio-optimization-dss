"""Generate transparent synthetic utterances from hand-authored intent seeds."""

from __future__ import annotations

import csv
from pathlib import Path

from app.assistant.intents import AssistantIntent

DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parent / "data" / "synthetic_qa_training.csv"
)
SYMBOLS = (
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ITC",
    "BHARTIARTL",
    "DIVISLAB",
    "M&M",
    "WIPRO",
    "AXISBANK",
    "BPCL",
    "HINDALCO",
    "EICHERMOT",
    "SUNPHARMA",
    "NTPC",
    "LTIM",
    "ASIANPAINT",
    "INDUSINDBK",
    "MARUTI",
    "TATASTEEL",
)
SECTORS = ("IT", "Energy", "Financial Services", "Automobile", "Pharma")

# Fifteen human-written phrasings per intent define meaning. Augmentation substitutes
# real-looking symbols/sectors/shocks and neutral conversational wrappers. This is a
# synthetic routing dataset, not a corpus of observed investor questions.
SEEDS: dict[AssistantIntent, tuple[str, ...]] = {
    AssistantIntent.EXPLAIN_STOCK_INCLUSION: (
        "why is {symbol} in my portfolio",
        "why did you include {symbol}",
        "explain the selection of {symbol}",
        "what made {symbol} get selected",
        "why was {symbol} bought",
        "reason for holding {symbol}",
        "why does my allocation contain {symbol}",
        "tell me why {symbol} is included",
        "what supports the {symbol} position",
        "why did the optimizer choose {symbol}",
        "justify including {symbol}",
        "why is money allocated to {symbol}",
        "what is the inclusion rationale for {symbol}",
        "why is {symbol} one of my holdings",
        "explain why we own {symbol}",
    ),
    AssistantIntent.EXPLAIN_STOCK_EXCLUSION: (
        "why is {symbol} not in my portfolio",
        "why did you exclude {symbol}",
        "explain the rejection of {symbol}",
        "what kept {symbol} out",
        "why was {symbol} not selected",
        "reason for excluding {symbol}",
        "why does my allocation omit {symbol}",
        "tell me why {symbol} is excluded",
        "what prevented a {symbol} position",
        "why did the optimizer reject {symbol}",
        "justify leaving out {symbol}",
        "why is no money allocated to {symbol}",
        "what is the exclusion rationale for {symbol}",
        "why is {symbol} missing from my holdings",
        "explain why we do not own {symbol}",
    ),
    AssistantIntent.PORTFOLIO_RISK_SUMMARY: (
        "how risky is my portfolio",
        "summarize my portfolio risk",
        "what is my volatility",
        "tell me the risk metrics",
        "what is the maximum drawdown",
        "how much risk am I taking",
        "show my sharpe and volatility",
        "describe the portfolio risk level",
        "what losses did the backtest show",
        "give me a risk summary",
        "is this portfolio high risk",
        "what is the realized risk",
        "explain my risk numbers",
        "how volatile are these holdings",
        "what does analytics say about risk",
    ),
    AssistantIntent.ALLOCATION_RATIONALE: (
        "why is the portfolio allocated this way",
        "explain the overall allocation",
        "what drove these weights",
        "summarize the optimization decision",
        "why are the weights like this",
        "give me the portfolio rationale",
        "how did the optimizer allocate my money",
        "explain the selected mix",
        "why this combination of stocks",
        "what is the logic behind the allocation",
        "describe the portfolio construction",
        "why did I get these holdings",
        "summarize why this portfolio was chosen",
        "what determined the allocation",
        "explain the overall investment mix",
    ),
    AssistantIntent.HYPOTHETICAL_SHOCK: (
        "what if the market {shock}",
        "simulate a {magnitude}% market {shock}",
        "how would a {magnitude}% crash affect me",
        "stress test a market {shock}",
        "what happens during a crash",
        "run a {shock} scenario",
        "what if interest rates rise {magnitude}%",
        "simulate an interest rate increase",
        "what if inflation rises {magnitude}%",
        "run an inflation shock",
        "what if the {sector} sector crashes",
        "stress the {sector} sector",
        "reoptimize after a {magnitude}% decline",
        "how does the portfolio change in a crash",
        "show a real market shock result",
    ),
    AssistantIntent.DIVERSIFICATION_QUESTION: (
        "how diversified is my portfolio",
        "explain my diversification score",
        "am I well diversified",
        "what is the concentration level",
        "show stock and sector concentration",
        "is my allocation concentrated",
        "describe diversification",
        "how spread out are my investments",
        "do I hold enough different assets",
        "what does the diversification metric mean",
        "is one sector dominating",
        "give me the concentration breakdown",
        "how balanced is the portfolio",
        "tell me about sector diversification",
        "what is my portfolio diversity",
    ),
    AssistantIntent.UNKNOWN: (
        "what is the weather today",
        "tell me a joke",
        "who won the football match",
        "write an email for me",
        "what is quantum physics",
        "book a restaurant",
        "play some music",
        "translate this sentence",
        "what is the capital of france",
        "set an alarm",
        "show movie times",
        "how do I bake bread",
        "give me world news",
        "what is your favorite color",
        "help me buy a phone",
    ),
}


def generate_training_records() -> list[dict[str, str]]:
    wrappers = (
        "",
        "please ",
        "can you ",
        "could you ",
        "I want to know: ",
        "help me understand: ",
        "for this snapshot, ",
        "using my data, ",
        "from the optimizer, ",
        "in simple terms, ",
        "show me: ",
        "tell me: ",
        "I am asking: ",
        "based on my portfolio, ",
        "from stored results, ",
        "quickly ",
        "clearly ",
        "for review, ",
        "for my report, ",
        "answer this: ",
    )
    records: set[tuple[str, str]] = set()
    for intent, seeds in SEEDS.items():
        for seed_index, seed in enumerate(seeds):
            for wrapper_index, wrapper in enumerate(wrappers):
                symbol = SYMBOLS[(seed_index + wrapper_index) % len(SYMBOLS)]
                sector = SECTORS[(seed_index + wrapper_index) % len(SECTORS)]
                magnitude = (5, 10, 15, 20, 25)[(seed_index + wrapper_index) % 5]
                shock = ("crashes", "falls", "declines", "drops")[
                    (seed_index + wrapper_index) % 4
                ]
                question = wrapper + seed.format(
                    symbol=symbol, sector=sector, magnitude=magnitude, shock=shock
                )
                records.add((question.strip(), intent.value))
    return [
        {"question": question, "intent": intent} for question, intent in sorted(records)
    ]


def write_training_csv(
    records: list[dict[str, str]], path: Path = DEFAULT_DATA_PATH
) -> Path:
    if not records:
        raise ValueError("records must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question", "intent"])
        writer.writeheader()
        writer.writerows(records)
    return path


def generate_training_data(path: Path = DEFAULT_DATA_PATH) -> Path:
    return write_training_csv(generate_training_records(), path)


if __name__ == "__main__":
    print(generate_training_data())
