export function createLatestRequest(request, onData, onError) {
  let current = null;

  return {
    async run() {
      current?.abort();
      const controller = new AbortController();
      current = controller;
      try {
        const data = await request(controller.signal);
        if (current === controller && !controller.signal.aborted) onData(data);
      } catch (error) {
        if (current === controller && !controller.signal.aborted) onError(error);
      }
    },
    cancel() {
      current?.abort();
      current = null;
    },
  };
}
