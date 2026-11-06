import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

BASE_MODEL = "unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit"
ADAPTER_PATH = "models/qwen_sql_adapter"

def load_model():

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map={"": 0},
        dtype=torch.float16
    )

    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    model.eval()

    return model, tokenizer


if __name__ == "__main__":
    model, tokenizer = load_model()
    question = "Find the second highest salary in each department using DENSE_RANK()."

    prompt = f"""Generate only SQL for this question:
{question}
SQL:"""

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        temperature=0.1
    )

    print(tokenizer.decode(outputs[0], skip_special_tokens=True))