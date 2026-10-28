# Offline Model Provenance

Models are published by Qwen / Alibaba Cloud and are not authored by this project.
The official quantized GGUF files are downloaded without modification and verified
against immutable revisions, exact byte limits and SHA-256 digests in policy.py.

- Actor: Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF, revision f86cb2c1fa58255f8052cc32aeede1b7482d4361.
- Reviewer: Qwen/Qwen2.5-Coder-7B-Instruct-GGUF, revision 13fb94bfda8c8cf22497dc57b78f391a9acb426a.
- Both official repositories declare Apache-2.0. The complete upstream license is
  retained as Qwen-LICENSE.txt and copied into the runtime cache alongside weights.
- Pinned reviewer license source: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/blob/13fb94bfda8c8cf22497dc57b78f391a9acb426a/LICENSE

The llama.cpp engine is separately MIT-licensed; its full original license remains
in the pinned downloaded source archive and compiled runtime source directory.
Model weights are not bundled in the Python wheel/source archive.