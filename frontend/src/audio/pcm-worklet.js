const TARGET_SAMPLE_RATE = 16000
const FRAME_SAMPLES = 1600

class PcmProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._ratio = sampleRate / TARGET_SAMPLE_RATE
    this._outBuf = new Float32Array(FRAME_SAMPLES)
    this._outIdx = 0
    this._inTail = new Float32Array(0)
    this._inPos = 0

    this.port.onmessage = (event) => {
      if (event.data?.type === 'reset') {
        this._outIdx = 0
        this._inTail = new Float32Array(0)
        this._inPos = 0
      }
    }
  }

  _emitFrame() {
    const buffer = new ArrayBuffer(FRAME_SAMPLES * 2)
    const view = new DataView(buffer)
    let sumSq = 0

    for (let i = 0; i < FRAME_SAMPLES; i += 1) {
      const s = this._outBuf[i]
      sumSq += s * s
      const scaled = s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff)
      const int16 = scaled < -32768 ? -32768 : (scaled > 32767 ? 32767 : scaled)
      view.setInt16(i * 2, int16, true)
    }

    const rms = Math.sqrt(sumSq / FRAME_SAMPLES)
    this.port.postMessage({ buffer, rms }, [buffer])
    this._outIdx = 0
  }

  _pushSample(sample) {
    const clamped = sample < -1 ? -1 : (sample > 1 ? 1 : sample)
    this._outBuf[this._outIdx] = clamped
    this._outIdx += 1
    if (this._outIdx === FRAME_SAMPLES) {
      this._emitFrame()
    }
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || input.length === 0 || !input[0] || input[0].length === 0) {
      return true
    }

    const ch0 = input[0]
    if (sampleRate === TARGET_SAMPLE_RATE) {
      for (let i = 0; i < ch0.length; i += 1) {
        this._pushSample(ch0[i])
      }
      return true
    }

    let buf = ch0
    if (this._inTail.length > 0) {
      buf = new Float32Array(this._inTail.length + ch0.length)
      buf.set(this._inTail, 0)
      buf.set(ch0, this._inTail.length)
    }

    while (Math.floor(this._inPos) + 1 < buf.length) {
      const idx = Math.floor(this._inPos)
      const frac = this._inPos - idx
      const sample = buf[idx] + (buf[idx + 1] - buf[idx]) * frac
      this._pushSample(sample)
      this._inPos += this._ratio
    }

    const consumed = Math.min(buf.length, Math.floor(this._inPos))
    this._inTail = buf.slice(consumed)
    this._inPos -= consumed
    return true
  }
}

registerProcessor('pcm-processor', PcmProcessor)
