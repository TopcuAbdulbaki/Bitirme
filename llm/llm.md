Responsible for text analysis. Will use qwen3 for text analysis. Will use asyncio for async operations. Will use langchain for AI operations. Python 3.13.5
There will be 2 version of this node. They will do exact same thing but one going to work with headless lm-studio as qwen3 vl-2b (this will be my prototype going to be used for testing on local) and the other one will be normal Huggingface model qwen3 8b (this will be my production version going to be used on server).
Both will have same functionality. Only difference is that one will work on headless lm-studio that loaded on my local and the other one will work on transformers(this will be my production version going to be used on server).

will get texts from crawler via orchestrator. will send analysis results to orchestrator.

Huggingface Model: https://huggingface.co/Qwen/Qwen3-8B
lm-studio Model: qwen3-vl-2b-instruct (you have to direct me to activate downloaded model on lm-studio)


Node Name: "LLM"
Node ID: 


analyzes texts and images analysis results and send its own analysis results to orchestrator as json file. It gonna be used for final analysis. interprates alltogether and sends short summary and if its positive(1) or negative(-1) or neutral(0) to orchestrator with structural way

