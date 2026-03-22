const GOLDEN_RATIO = (1 + Math.sqrt(5)) / 2

function normalize([x, y, z]) {
  const len = Math.hypot(x, y, z) || 1
  return [x / len, y / len, z / len]
}

function scaleVertex([x, y, z], radius) {
  return [x * radius, y * radius, z * radius]
}

function dot(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

function cross(a, b) {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0]
  ]
}

function faceNormal(faceVertices) {
  const [a, b, c] = faceVertices
  const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
  const ac = [c[0] - a[0], c[1] - a[1], c[2] - a[2]]
  return normalize([
    ab[1] * ac[2] - ab[2] * ac[1],
    ab[2] * ac[0] - ab[0] * ac[2],
    ab[0] * ac[1] - ab[1] * ac[0]
  ])
}

function buildFaces(vertices, indices) {
  return indices.map((faceIdx) => {
    const faceVertices = faceIdx.map((idx) => vertices[idx])
    return {
      indices: faceIdx,
      vertices: faceVertices,
      normal: faceNormal(faceVertices)
    }
  })
}

function sortFaceVertices(indices, allVertices, normal) {
  if (indices.length <= 2) return indices

  const center = [0, 0, 0]
  indices.forEach((idx) => {
    const v = allVertices[idx]
    center[0] += v[0]
    center[1] += v[1]
    center[2] += v[2]
  })
  center[0] /= indices.length
  center[1] /= indices.length
  center[2] /= indices.length

  // 在面平面内构造局部坐标轴，用于按极角排序。
  const refAxis = Math.abs(normal[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]
  const axisU = normalize(cross(normal, refAxis))
  const axisV = normalize(cross(normal, axisU))

  return [...indices].sort((a, b) => {
    const va = allVertices[a]
    const vb = allVertices[b]
    const pa = [va[0] - center[0], va[1] - center[1], va[2] - center[2]]
    const pb = [vb[0] - center[0], vb[1] - center[1], vb[2] - center[2]]

    const angleA = Math.atan2(dot(pa, axisV), dot(pa, axisU))
    const angleB = Math.atan2(dot(pb, axisV), dot(pb, axisU))
    return angleA - angleB
  })
}

export function createTetrahedron(radius = 100) {
  const vertices = [
    [1, 1, 1],
    [-1, -1, 1],
    [-1, 1, -1],
    [1, -1, -1]
  ].map((v) => scaleVertex(normalize(v), radius))

  const faces = buildFaces(vertices, [
    [0, 1, 2],
    [0, 3, 1],
    [0, 2, 3],
    [1, 3, 2]
  ])
  return { vertices, faces }
}

export function createOctahedron(radius = 100) {
  const vertices = [
    [1, 0, 0],
    [-1, 0, 0],
    [0, 1, 0],
    [0, -1, 0],
    [0, 0, 1],
    [0, 0, -1]
  ].map((v) => scaleVertex(v, radius))

  const faces = buildFaces(vertices, [
    [0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
    [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]
  ])
  return { vertices, faces }
}

export function createIcosahedron(radius = 100) {
  const p = GOLDEN_RATIO
  const vertices = [
    [-1, p, 0], [1, p, 0], [-1, -p, 0], [1, -p, 0],
    [0, -1, p], [0, 1, p], [0, -1, -p], [0, 1, -p],
    [p, 0, -1], [p, 0, 1], [-p, 0, -1], [-p, 0, 1]
  ].map((v) => scaleVertex(normalize(v), radius))

  const faces = buildFaces(vertices, [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
  ])
  return { vertices, faces }
}

export function createDodecahedron(radius = 100) {
  const icosa = createIcosahedron(1)
  const vertices = icosa.faces.map((f) => scaleVertex(f.normal, radius))

  const faces = icosa.vertices.map((v, vertexIndex) => {
    const adjacent = []
    icosa.faces.forEach((face, faceIndex) => {
      if (face.indices.includes(vertexIndex)) adjacent.push(faceIndex)
    })

    const normal = normalize(v)
    const sorted = sortFaceVertices(adjacent, vertices, normal)

    return {
      indices: sorted,
      vertices: sorted.map((idx) => vertices[idx]),
      normal
    }
  })

  return { vertices, faces }
}

