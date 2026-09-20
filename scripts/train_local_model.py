"""
Fine-Tuning Script for GraphRAG Research Notebook SLM.

This script uses QLoRA to efficiently fine-tune a small language model
on the locally cached dataset (`data/sample_hotpotqa.json`).

Requirements:
- NVIDIA GPU (CUDA) recommended.
- pip install torch transformers peft trl bitsandbytes datasets accelerate
"""

import os
import json
import argparse
from typing import Dict, Any

try:
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please run: pip install torch transformers peft trl bitsandbytes datasets accelerate")
    exit(1)


def format_dataset(dataset_path: str) -> Dataset:
    """
    Loads `sample_hotpotqa.json` and formats it into conversational prompts
    for instruction tuning.
    """
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Run loader first.")
        
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = data.get("records", [])
    
    formatted_data = {"text": []}
    for record in records:
        question = record["question"]
        answer = record["answer"]
        # In HotpotQA, context is a list of [title, list of sentences]
        context_parts = []
        for ctx in record.get("context", []):
            title = ctx[0]
            text = " ".join(ctx[1])
            context_parts.append(f"Title: {title}\n{text}")
            
        full_context = "\n\n".join(context_parts)
        
        # Build prompt that mimics our RAG generation template
        prompt = (
            f"<|im_start|>system\nYou are a helpful, accurate research assistant. "
            f"Answer the user's question using ONLY the provided context.<|im_end|>\n"
            f"<|im_start|>user\nCONTEXT SOURCES:\n{full_context}\n\n"
            f"QUESTION: {question}<|im_end|>\n"
            f"<|im_start|>assistant\n{answer}<|im_end|>"
        )
        formatted_data["text"].append(prompt)
        
    print(f"Loaded {len(formatted_data['text'])} examples for training.")
    return Dataset.from_dict(formatted_data)


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Local SLM using QLoRA")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-1.5B-Instruct", help="Base model ID")
    parser.add_argument("--dataset", type=str, default="data/sample_hotpotqa.json", help="Path to sample dataset")
    parser.add_argument("--output_dir", type=str, default="models/qwen-hotpotqa-lora", help="Output directory")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--dry_run", action="store_true", help="Format data and exit without training")
    args = parser.parse_args()

    # 1. Load dataset
    dataset = format_dataset(args.dataset)
    if args.dry_run:
        print("\nDry run requested. Here is a sample formatted prompt:")
        print("-" * 50)
        print(dataset[0]["text"])
        print("-" * 50)
        return

    # 2. Configure QLoRA (4-bit quantization)
    print("Configuring 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    )

    # 3. Load Model and Tokenizer
    print(f"Loading base model: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    model = prepare_model_for_kbit_training(model)

    # 4. LoRA Adapter Config
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 5. Training Arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=5,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
        remove_unused_columns=False,
    )

    # 6. Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=1024,
        tokenizer=tokenizer,
        args=training_args,
    )

    # 7. Start Training
    print("Starting training...")
    trainer.train()

    # 8. Save Final Model
    print(f"Saving fine-tuned adapter to {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Training complete!")

if __name__ == "__main__":
    main()
