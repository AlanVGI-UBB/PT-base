export async function iniciar({ onTrama, onNivel } = {}) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: true,
    },
  })

  let ctx
  try {
    // Usar frecuencia nativa del hardware evita silencios de WASAPI/Bluetooth al forzar 16 kHz;
    // pcm-worklet.js remuestrea a 16 kHz cuando sampleRate !== 16000.
    ctx = new AudioContext()
    if (ctx.state === 'suspended') {
      await ctx.resume()
    }

    await ctx.audioWorklet.addModule(new URL('./pcm-worklet.js', import.meta.url))

    const source = ctx.createMediaStreamSource(stream)
    const worklet = new AudioWorkletNode(ctx, 'pcm-processor', {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      channelCount: 1,
      channelCountMode: 'explicit',
    })
    const silenceGain = ctx.createGain()
    silenceGain.gain.value = 0

    source.connect(worklet)
    worklet.connect(silenceGain)
    silenceGain.connect(ctx.destination)

    let pausado = false
    let detenido = false

    worklet.port.onmessage = (event) => {
      if (detenido || pausado) return
      const { buffer, rms } = event.data
      onNivel?.(rms)
      onTrama?.(buffer)
    }

    return {
      pausar() {
        pausado = true
      },
      reanudar() {
        if (detenido) return
        worklet.port.postMessage({ type: 'reset' })
        pausado = false
      },
      async detener() {
        if (detenido) return
        detenido = true
        worklet.port.onmessage = null
        try {
          source.disconnect()
          worklet.disconnect()
          silenceGain.disconnect()
        } catch {
          // nodos ya desconectados
        }
        stream.getTracks().forEach((t) => t.stop())
        if (ctx.state !== 'closed') {
          await ctx.close().catch(() => {})
        }
      },
    }
  } catch (err) {
    stream.getTracks().forEach((t) => t.stop())
    if (ctx && ctx.state !== 'closed') {
      await ctx.close().catch(() => {})
    }
    throw err
  }
}
