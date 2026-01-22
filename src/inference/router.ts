import Anthropic from '@anthropic-ai/sdk';

export interface InferenceBackend {
  name: string;
  type: 'anthropic' | 'ollama' | 'openai';
  model: string;
  baseUrl?: string;
}

export interface InferenceRequest {
  input: string;
  systemPrompt?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface InferenceResponse {
  output: string;
  model: string;
  tokensUsed?: number;
  latencyMs: number;
}

export class InferenceRouter {
  private backends: Map<string, InferenceBackend> = new Map();
  private anthropic?: Anthropic;
  private defaultBackend: string;

  constructor(backends: InferenceBackend[], defaultBackend: string) {
    for (const backend of backends) {
      this.backends.set(backend.name, backend);

      if (backend.type === 'anthropic') {
        this.anthropic = new Anthropic();
      }
    }

    this.defaultBackend = defaultBackend;
  }

  async infer(request: InferenceRequest, backendName?: string): Promise<InferenceResponse> {
    const backend = this.backends.get(backendName || this.defaultBackend);
    if (!backend) {
      throw new Error(`Backend ${backendName || this.defaultBackend} not configured`);
    }

    const startTime = Date.now();

    switch (backend.type) {
      case 'anthropic':
        return this.inferAnthropic(request, backend, startTime);

      case 'ollama':
        return this.inferOllama(request, backend, startTime);

      default:
        throw new Error(`Unsupported backend type: ${backend.type}`);
    }
  }

  private async inferAnthropic(
    request: InferenceRequest,
    backend: InferenceBackend,
    startTime: number
  ): Promise<InferenceResponse> {
    if (!this.anthropic) {
      throw new Error('Anthropic client not initialized');
    }

    const response = await this.anthropic.messages.create({
      model: backend.model,
      max_tokens: request.maxTokens || 1024,
      system: request.systemPrompt || 'You are a helpful, reflective assistant. Avoid prescriptive language.',
      messages: [
        { role: 'user', content: request.input }
      ]
    });

    const output = response.content
      .filter(block => block.type === 'text')
      .map(block => (block as { type: 'text'; text: string }).text)
      .join('\n');

    return {
      output,
      model: backend.model,
      tokensUsed: response.usage?.output_tokens,
      latencyMs: Date.now() - startTime
    };
  }

  private async inferOllama(
    request: InferenceRequest,
    backend: InferenceBackend,
    startTime: number
  ): Promise<InferenceResponse> {
    const baseUrl = backend.baseUrl || 'http://localhost:11434';

    const response = await fetch(`${baseUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: backend.model,
        prompt: request.input,
        system: request.systemPrompt,
        stream: false
      })
    });

    if (!response.ok) {
      throw new Error(`Ollama error: ${response.status}`);
    }

    const data = await response.json() as { response: string };

    return {
      output: data.response,
      model: backend.model,
      latencyMs: Date.now() - startTime
    };
  }

  getAvailableBackends(): string[] {
    return Array.from(this.backends.keys());
  }
}
