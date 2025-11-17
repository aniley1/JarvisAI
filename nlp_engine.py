# core/nlp_engine.py

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

class NLPEngine:
    def __init__(self):
        print("[INFO] Loading NLP model...")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
        self.model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")
        self.chat_history_ids = None

    def generate_response(self, user_input):
        input_ids = self.tokenizer.encode(user_input + self.tokenizer.eos_token, return_tensors='pt')

        if self.chat_history_ids is not None:
            bot_input_ids = torch.cat([self.chat_history_ids, input_ids], dim=-1)
        else:
            bot_input_ids = input_ids

        self.chat_history_ids = self.model.generate(bot_input_ids, max_length=1000, pad_token_id=self.tokenizer.eos_token_id)
        response = self.tokenizer.decode(self.chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)

        return response
