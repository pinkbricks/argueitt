// Encodes an AudioBuffer as a 16-bit PCM WAV Blob.
export function audioBufferToWavBlob(audioBuffer) {
  const numChannels = audioBuffer.numberOfChannels
  const sampleRate = audioBuffer.sampleRate
  const numFrames = audioBuffer.length
  const bytesPerSample = 2
  const blockAlign = numChannels * bytesPerSample
  const dataSize = numFrames * blockAlign

  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  const writeString = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM format
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true) // byte rate
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 8 * bytesPerSample, true) // bits per sample
  writeString(36, 'data')
  view.setUint32(40, dataSize, true)

  const channels = []
  for (let ch = 0; ch < numChannels; ch++) channels.push(audioBuffer.getChannelData(ch))

  let offset = 44
  for (let frame = 0; frame < numFrames; frame++) {
    for (let ch = 0; ch < numChannels; ch++) {
      const sample = Math.max(-1, Math.min(1, channels[ch][frame]))
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
      offset += bytesPerSample
    }
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

// Decodes a recorded audio Blob (e.g. webm/opus) and re-encodes it as a WAV Blob.
export async function toWavBlob(blob) {
  const arrayBuffer = await blob.arrayBuffer()
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  const ctx = new AudioContextClass()
  try {
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer)
    return audioBufferToWavBlob(audioBuffer)
  } finally {
    ctx.close()
  }
}
