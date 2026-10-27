FROM python:3.13-slim-bookworm AS compiler
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake && rm -rf /var/lib/apt/lists/*
COPY llama /llama
RUN cmake -S /llama -B /llama/build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF && cmake --build /llama/build --target llama-completion -j 2
FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=compiler /llama /opt/llama
USER 10001:10001
ENTRYPOINT ["/opt/llama/build/bin/llama-completion"]