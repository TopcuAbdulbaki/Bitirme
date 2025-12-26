Responsible for image analysis. Will use qwen3 for image analysis. Will use asyncio for async operations. Will use langchain for AI operations. Python 3.13.5
There will be 2 version of this node. They will do exact same thing but one going to work with headless lm-studio as qwen3 vl-2b (this will be my prototype going to be used for testing on local) and the other one will be normal Huggingface model qwen3 vl-8b (this will be my production version going to be used on server).
Both will have same functionality. Only difference is that one will work on headless lm-studio that loaded on my local and the other one will work on transformers(this will be my production version going to be used on server).

will get images and texts that crawler extracted and send as json file from orchestrator. will send analysis results to orchestrator.

Huggingface Model: https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct
lm-studio Model: qwen3-vl-2b-instruct (you have to direct me to activate downloaded model on lm-studio)

Node Name: "VLM"
Node ID: 

Its analyze images and for each image it gonna send analysis results to orchestrator. as json file