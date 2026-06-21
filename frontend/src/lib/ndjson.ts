export type NdjsonParseSuccess<T> = {
  ok: true;
  value: T;
};

export type NdjsonParseFailure = {
  ok: false;
  line: string;
  error: Error;
};

export type NdjsonParseItem<T> = NdjsonParseSuccess<T> | NdjsonParseFailure;

export type NdjsonConsumeResult<T> = {
  items: NdjsonParseItem<T>[];
  buffer: string;
};

export function consumeNdjson<T = unknown>(
  buffer: string,
  chunk: string,
): NdjsonConsumeResult<T> {
  const combined = buffer + chunk;
  const lines = combined.split(/\r?\n/);
  const nextBuffer = lines.pop() ?? "";
  const items: NdjsonParseItem<T>[] = [];

  for (const line of lines) {
    if (!line.trim()) {
      continue;
    }

    try {
      items.push({ ok: true, value: JSON.parse(line) as T });
    } catch (cause) {
      const error = cause instanceof Error ? cause : new Error(String(cause));
      items.push({ ok: false, line, error });
    }
  }

  return { items, buffer: nextBuffer };
}

export function flushNdjson<T = unknown>(buffer: string): NdjsonParseItem<T>[] {
  const line = buffer.trim();
  if (!line) {
    return [];
  }

  try {
    return [{ ok: true, value: JSON.parse(line) as T }];
  } catch (cause) {
    const error = cause instanceof Error ? cause : new Error(String(cause));
    return [{ ok: false, line, error }];
  }
}
