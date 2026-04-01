from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
from transformers import AutoProcessor

model_id = "openai/whisper-tiny"
output_path = "./whisper_onnx"

print("baixando e convertento... Isso pode demorar alguns minutos no Pi.")

model = ORTModelForSpeechSeq2Seq.from_pretrained(model_id, export=True)
processor = AutoProcessor.from_pretrained(model_id)

model.save_pretrained(output_path)
processor.save_pretrained(output_path)

print("Pronto! Modelo salvo em: {output_path}")