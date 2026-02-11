from api.attribution.models.source import InfiGramSourceList, InfiniGramSource

# fmt: off
INFINI_GRAM_SOURCES = InfiGramSourceList(
    InfiniGramSource(
        name="dclm",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="web corpus (DCLM)"
    ),
    InfiniGramSource(
        name="dclm-hero-run-fasttext_for_HF",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="web corpus (DCLM)"
    ),
    InfiniGramSource(
        name="arxiv",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="arxiv"
    ),
    InfiniGramSource(
        name="algebraic-stack",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="algebraic-stack"
    ),
    InfiniGramSource(
        name="open-web-math",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="open-web-math"
    ),
    InfiniGramSource(
        name="pes2o",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="pes2o"
    ),
    InfiniGramSource(
        name="starcoder",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="starcoder"
    ),
    InfiniGramSource(
        name="wiki",
        usage="Pre-training",
        display_name="olmo-mix-1124",
        secondary_name="wiki"
    ),
    InfiniGramSource(
        name="dolmino",
        usage="Mid-training",
        display_name="dolmino-mix-1124"
    ),
    InfiniGramSource(
        name="tulu-3-sft-olmo-2-mixture",
        usage="Post-training (SFT)"
    ),
    InfiniGramSource(
        name="tulu-3-sft-olmo-2-mixture-0225",
        usage="Post-training (SFT)"
    ),
    InfiniGramSource(
        name="olmoe-0125-1b-7b-preference-mix",
        usage="Post-training (DPO)"
    ),
    InfiniGramSource(
        name="olmo-2-1124-13b-preference-mix",
        usage="Post-training (DPO)"
    ),
    InfiniGramSource(
        name="olmo-2-0325-32b-preference-mix",
        usage="Post-training (DPO)"
    ),
    InfiniGramSource(
        name="RLVR-GSM",
        usage="Post-training (RLVR)"
    ),
    InfiniGramSource(
        name="RLVR-GSM-MATH-IF-Mixed-Constraints",
        usage="Post-training (RLVR)"
    ),
    InfiniGramSource(
        name="tulu-3-sft-mixture",
        usage="Post-training (SFT)"
    ),
    InfiniGramSource(
        name="llama-3.1-tulu-3-8b-preference-mixture",
        usage="Post-training (DPO)"
    ),
    InfiniGramSource(
        name="llama-3.1-tulu-3-70b-preference-mixture",
        usage="Post-training (DPO)"
    ),
    InfiniGramSource(
        name="llama-3.1-tulu-3-405b-preference-mixture",
        usage="Post-training (DPO)"
    ),
    InfiniGramSource(
        name="RLVR-MATH",
        usage="Post-training (RLVR)"
    ),
)
