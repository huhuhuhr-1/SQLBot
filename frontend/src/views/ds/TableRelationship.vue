<script lang="ts" setup>
import { onMounted, onBeforeUnmount, ref, nextTick, watch } from 'vue'
import { datasourceApi } from '@/api/datasource'
import { useI18n } from 'vue-i18n'
import { Graph, Cell, Shape } from '@antv/x6'
import { debounce } from 'lodash-es'
import { Plus, Minus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus-secondary'
import { Graph as LayoutGraph } from '@antv/graphlib'
import { DagreLayout, D3ForceLayout, RadialLayout } from '@antv/layout'

const FIRST_PORT_Y = 51
const PORT_ROW_H = 46
const NODE_WIDTH = 180
const GRID_COLS = 4
const GRID_STEP_X = 220
const GRID_STEP_Y = 280
const LAYOUT_GAP_Y = 24
/** 布局器防重叠：在节点外接圆直径上额外加的间隙（@antv layout 里 nodeSize 多按直径/碰撞圆） */
const LAYOUT_NODE_SEPARATION = 44

const getPortCount = (node: any) => (node.getPorts?.() ?? []).length
const getNodeHeightForPortCount = (n: number) => FIRST_PORT_Y + n * PORT_ROW_H

/** 长方形节点用外接圆直径 + 间隙，径向/力导防重叠才够 */
const getLayoutNodeSizeDiameter = (cell: any | null) => {
  const w = cell?.getBBox?.()?.width ?? NODE_WIDTH
  const h = cell?.getBBox?.()?.height ?? getNodeHeightForPortCount(1)
  return Math.ceil(Math.hypot(w, h) + LAYOUT_NODE_SEPARATION)
}

const props = withDefaults(
  defineProps<{
    id: number
    dragging: boolean
  }>(),
  {
    id: 0,
    dragging: false,
  }
)

const emits = defineEmits(['getTableName', 'openTableDetail'])

const { t } = useI18n()
const loading = ref(false)
const tooltipY = ref('-999px')
const tooltipX = ref('-999px')
const tooltipContent = ref('')
const nodeIds = ref<any[]>([])
const cells = ref<Cell[]>([])
const showAllFields = ref(false)

const fullFieldsCache = new Map<string, any[]>()
const tableMetaCache = new Map<string, { table_name: string; custom_comment?: string; table_comment?: string }>()

const edgeOPtion = {
  tools: [
    {
      name: 'button-remove',
      args: { x: 20, y: 20 },
    },
  ],
  attrs: {
    line: {
      stroke: '#DEE0E3',
      strokeWidth: 2,
    },
  },
}
let graph: any

const resetTooltip = () => {
  tooltipY.value = '-1000px'
  tooltipX.value = '-1000px'
  tooltipContent.value = ''
}

const fieldCommentText = (f: any) => String(f?.custom_comment || f?.field_comment || '').trim()

const fieldsToPortItems = (fields: any[]) =>
  (fields || []).map((ele) => {
    const cmt = fieldCommentText(ele)
    return {
      id: ele.id,
      group: 'list',
      attrs: {
        portNameLabel: { text: String(ele.field_name ?? '') },
        portCommentLabel: { text: cmt },
        portTypeLabel: { text: ele.field_type },
      },
    }
  })

const nodeLabelAttrs = (table: any) => {
  const cmt = String(table?.custom_comment || table?.table_comment || '').trim()
  return {
    label: {
      text: String(table?.table_name ?? ''),
      textAnchor: 'left',
      refX: 34,
      refY: 22,
      textWrap: {
        width: 120,
        height: 22,
        ellipsis: true,
      },
    },
    labelComment: {
      text: cmt,
      textAnchor: 'left',
      refX: 34,
      refY: 44,
      fill: '#646A73',
      fontSize: 11,
      textWrap: {
        width: 125,
        height: 16,
        ellipsis: true,
      },
    },
  }
}

const portsToFields = (ports: any[]): any[] =>
  (ports || []).map((p) => ({
    id: p.id,
    field_name: p.attrs?.portNameLabel?.text ?? '',
    field_type: p.attrs?.portTypeLabel?.text ?? '',
    custom_comment: p.attrs?.portCommentLabel?.text ?? '',
    field_comment: '',
  }))

const rememberTableMeta = (id: string | number, table: any) => {
  tableMetaCache.set(String(id), {
    table_name: String(table?.table_name ?? ''),
    custom_comment: table?.custom_comment,
    table_comment: table?.table_comment,
  })
}

const connectedPortIdsForCell = (cellId: string) => {
  const set = new Set<string>()
  if (!graph) return set
  graph.getEdges().forEach((edge: any) => {
    const s = edge.getSource()
    const tg = edge.getTarget()
    if (String(s.cell) === cellId && s.port != null) set.add(String(s.port))
    if (String(tg.cell) === cellId && tg.port != null) set.add(String(tg.port))
  })
  return set
}

const filterFieldsForDisplay = (cellId: string, full: any[]) => {
  if (!full.length) return full
  const conn = connectedPortIdsForCell(cellId)
  if (showAllFields.value || conn.size === 0) return full
  return full.filter((f) => conn.has(String(f.id)))
}

const refreshPortsOnGraph = () => {
  if (!graph) return
  graph.getNodes().forEach((node: any) => {
    const id = String(node.id)
    const full = fullFieldsCache.get(id)
    if (!full) return
    const fields = filterFieldsForDisplay(id, full)
    const portItems = fieldsToPortItems(fields)
    const curPorts = node.getProp('ports')
    const nextPorts =
      curPorts && typeof curPorts === 'object' && !Array.isArray(curPorts)
        ? { ...curPorts, items: portItems }
        : { items: portItems }
    node.setProp('ports', nextPorts)
    node.resize(NODE_WIDTH, getNodeHeightForPortCount(portItems.length))
  })
}

const refreshPortsDebounced = debounce(refreshPortsOnGraph, 80)

const buildNodePayload = (table: any, fields: any[]) => {
  const id = String(table.id)
  rememberTableMeta(id, table)
  fullFieldsCache.set(id, fields)
  const shown = filterFieldsForDisplay(id, fields)
  const ports = fieldsToPortItems(shown)
  return {
    id: table.id,
    shape: 'er-rect',
    data: {
      tableCustomComment: table.custom_comment,
      tableComment: table.table_comment,
    },
    attrs: nodeLabelAttrs(table),
    ports: { items: ports },
    width: NODE_WIDTH,
    height: getNodeHeightForPortCount(ports.length),
  }
}

const preprocessLoadedCells = (data: any[]) => {
  const edges = data.filter((i) => i.shape === 'edge')
  const mapConn = new Map<string, Set<string>>()
  edges.forEach((e) => {
    const s = String(e.source?.cell)
    const t = String(e.target?.cell)
    if (!mapConn.has(s)) mapConn.set(s, new Set())
    if (!mapConn.has(t)) mapConn.set(t, new Set())
    if (e.source?.port != null) mapConn.get(s)!.add(String(e.source.port))
    if (e.target?.port != null) mapConn.get(t)!.add(String(e.target.port))
  })
  return data.map((item) => {
    if (item.shape !== 'er-rect') return item
    const { label: _removedTopLevelLabel, ...itemSansTopLabel } = item
    void _removedTopLevelLabel
    const id = String(item.id)
    const fullPorts = item.ports?.items ?? item.ports ?? []
    const arr = Array.isArray(fullPorts) ? fullPorts : []
    fullFieldsCache.set(id, portsToFields(arr))
    const metaName = item.attrs?.label?.text ?? item.label
    tableMetaCache.set(id, {
      table_name: String(metaName ?? ''),
      custom_comment: item.data?.tableCustomComment,
      table_comment: item.data?.tableComment,
    })
    const conn = mapConn.get(id) ?? new Set()
    const useAll = showAllFields.value || conn.size === 0
    const filteredItems = useAll ? arr : arr.filter((p: any) => conn.has(String(p.id)))
    const portsShape =
      item.ports && typeof item.ports === 'object' && !Array.isArray(item.ports)
        ? { ...item.ports, items: filteredItems }
        : { items: filteredItems }
    const h = getNodeHeightForPortCount(filteredItems.length)
    return {
      ...itemSansTopLabel,
      ports: portsShape,
      width: NODE_WIDTH,
      height: h,
      attrs: {
        ...item.attrs,
        ...nodeLabelAttrs(tableMetaCache.get(id)),
      },
    }
  })
}

/** 用当前数据源的表列表 + 字段列表刷新画布上的中英文注释（修复旧存档或仅英文的端口数据） */
const hydrateCanvasCommentsFromApi = async () => {
  if (!graph || !props.id || !nodeIds.value.length) return
  try {
    const tables = (await datasourceApi.tableList(props.id)) as any[]
    const tableById = new Map(tables.map((t) => [String(t.id), t]))
    await Promise.all(
      nodeIds.value.map(async (nid) => {
        const tid = String(nid)
        const meta = tableById.get(tid)
        if (meta) {
          rememberTableMeta(tid, meta)
          const node = graph.getCellById(tid)
          if (node?.isNode?.()) {
            node.setAttrs(nodeLabelAttrs(meta))
            const prev = node.getData() || {}
            node.setData({
              ...prev,
              tableCustomComment: meta.custom_comment,
              tableComment: meta.table_comment,
            })
          }
        }
        const numId = typeof nid === 'number' ? nid : Number.parseInt(tid, 10)
        const fields = await datasourceApi.fieldList(numId)
        fullFieldsCache.set(tid, fields as any[])
      })
    )
    refreshPortsOnGraph()
  } catch {
    /* 列表无权限等错误时不阻塞画布 */
  }
}

const x6ToLayoutGraph = (x6: any): LayoutGraph<any, any> => {
  const nodes = x6.getNodes().map((n: any) => {
    const bbox = n.getBBox()
    return {
      id: String(n.id),
      data: { size: [bbox.width, bbox.height] },
    }
  })
  const edges = x6.getEdges().map((e: any, i: number) => ({
    id: `rel-e-${i}-${e.id}`,
    source: String(e.getSourceCellId()),
    target: String(e.getTargetCellId()),
  }))
  return new LayoutGraph<any, any>({ nodes, edges })
}

/** 边数最多的表作为径向布局中心（度相同则 id 较小者优先，稳定） */
const findHubNodeIdForRadial = (x6: any): string | null => {
  const nodes = x6.getNodes()
  if (!nodes.length) return null
  const degree = new Map<string, number>()
  nodes.forEach((n: any) => degree.set(String(n.id), 0))
  x6.getEdges().forEach((edge: any) => {
    const s = String(edge.getSourceCellId())
    const t = String(edge.getTargetCellId())
    degree.set(s, (degree.get(s) ?? 0) + 1)
    degree.set(t, (degree.get(t) ?? 0) + 1)
  })
  const sorted = [...degree.entries()].sort((a, b) => {
    if (b[1] !== a[1]) return b[1] - a[1]
    return a[0].localeCompare(b[0], undefined, { numeric: true })
  })
  return sorted[0]?.[0] ?? String(nodes[0].id)
}

const applyLayoutMapping = (mapping: { nodes: any[] }) => {
  mapping.nodes.forEach(({ id, data }: any) => {
    const cell = graph.getCellById(id)
    if (!cell?.isNode?.()) return
    const bbox = cell.getBBox()
    const w = bbox.width
    const h = bbox.height
    const x = (data?.x ?? 0) - w / 2
    const y = (data?.y ?? 0) - h / 2
    cell.setPosition(x, y)
  })
}

/** 轴对齐包围盒轻微穿透时推开节点（矩形表节点比「圆直径」更难一次排开） */
const easeAxisAlignedOverlaps = () => {
  if (!graph) return
  const gap = 10
  for (let pass = 0; pass < 16; pass++) {
    const nodes = graph.getNodes()
    let settled = true
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const A = nodes[i]
        const B = nodes[j]
        const pa = A.position()
        const pb = B.position()
        const ra = A.getBBox()
        const rb = B.getBBox()
        const l1 = pa.x - gap
        const t1 = pa.y - gap
        const r1 = pa.x + ra.width + gap
        const b1 = pa.y + ra.height + gap
        const l2 = pb.x - gap
        const t2 = pb.y - gap
        const r2 = pb.x + rb.width + gap
        const b2 = pb.y + rb.height + gap
        const ix = Math.min(r1, r2) - Math.max(l1, l2)
        const iy = Math.min(b1, b2) - Math.max(t1, t2)
        if (ix > 0 && iy > 0) {
          settled = false
          const cx1 = pa.x + ra.width / 2
          const cy1 = pa.y + ra.height / 2
          const cx2 = pb.x + rb.width / 2
          const cy2 = pb.y + rb.height / 2
          let dx = cx1 - cx2
          let dy = cy1 - cy2
          let len = Math.hypot(dx, dy)
          if (len < 1e-3) {
            dx = 1
            dy = 0
            len = 1
          }
          dx /= len
          dy /= len
          const shift = Math.max(ix, iy) / 2 + 8
          A.translate(dx * shift, dy * shift)
          B.translate(-dx * shift, -dy * shift)
        }
      }
    }
    if (settled) break
  }
}

const runDagreLayout = async () => {
  if (!graph || !graph.getNodes().length) return
  const lg = x6ToLayoutGraph(graph)
  const pad = Math.ceil(LAYOUT_NODE_SEPARATION / 2)
  const layout = new DagreLayout({
    rankdir: 'LR',
    nodesep: 88,
    ranksep: 128,
    nodeSize: (node: any) => {
      const cell = graph.getCellById(node.id)
      if (!cell) {
        return [NODE_WIDTH + pad, getNodeHeightForPortCount(1) + pad]
      }
      const { width, height } = cell.getBBox()
      return [Math.ceil(width + pad), Math.ceil(height + pad)]
    },
  } as any)
  const mapping = await layout.execute(lg)
  applyLayoutMapping(mapping)
  easeAxisAlignedOverlaps()
  nextTick(() => graph.zoomToFit({ padding: 80 }))
}

const runForceLayout = async () => {
  if (!graph || !graph.getNodes().length) return
  const lg = x6ToLayoutGraph(graph)
  const rect = graph.container.getBoundingClientRect()
  const cx = rect.width / 2 || 400
  const cy = rect.height / 2 || 300
  const layout = new D3ForceLayout({
    center: { x: cx, y: cy },
    iterations: 380,
    nodeSize: (_n: any, i: number, arr: any[]) => {
      const c = graph.getCellById(arr[i].id)
      return getLayoutNodeSizeDiameter(c)
    },
  })
  const mapping = await layout.execute(lg)
  applyLayoutMapping(mapping)
  easeAxisAlignedOverlaps()
  nextTick(() => graph.zoomToFit({ padding: 80 }))
}

const runRadialLayout = async () => {
  if (!graph || !graph.getNodes().length) return
  const focus = findHubNodeIdForRadial(graph)
  if (!focus) return
  const lg = x6ToLayoutGraph(graph)
  const rect = graph.container.getBoundingClientRect()
  const layoutW = Math.max(rect.width || 0, 720)
  const layoutH = Math.max(rect.height || 0, 560)
  const layout = new RadialLayout({
    focusNode: focus,
    /** 不传 unitRadius：按画布与最大深度自适应环距，避免固定像素把多节点挤成一团 */
    unitRadius: null,
    preventOverlap: true,
    /** 允许同环节点沿环前后错位，更易消除重叠 */
    strictRadial: true,
    nodeSpacing: Math.max(28, Math.floor(LAYOUT_NODE_SEPARATION * 0.75)),
    maxPreventOverlapIteration: 800,
    nodeSize: (node: any) => getLayoutNodeSizeDiameter(graph.getCellById(node.id)),
    width: layoutW,
    height: layoutH,
    center: [layoutW / 2, layoutH / 2],
  })
  const mapping = await layout.execute(lg)
  applyLayoutMapping(mapping)
  easeAxisAlignedOverlaps()
  nextTick(() => graph.zoomToFit({ padding: 80 }))
}

const getNodeHeight = (node: any) => getNodeHeightForPortCount(getPortCount(node))

const initGraph = () => {
  Graph.registerPortLayout(
    'erPortPosition',
    (portsPositionArgs) => {
      return portsPositionArgs.map((_, index) => {
        return {
          position: {
            x: 0,
            y: FIRST_PORT_Y + index * PORT_ROW_H,
          },
          angle: 0,
        }
      })
    },
    true
  )

  Graph.registerNode(
    'er-rect',
    {
      inherit: 'rect',
      markup: [
        { tagName: 'path', selector: 'top' },
        { tagName: 'rect', selector: 'body' },
        { tagName: 'text', selector: 'label' },
        { tagName: 'text', selector: 'labelComment' },
        { tagName: 'path', selector: 'div' },
      ],
      attrs: {
        top: {
          fill: '#BBBFC4',
          refX: 0,
          refY: 0,
          d: 'M0 5C0 2.23858 2.23858 0 5 0H175C177.761 0 180 2.23858 180 5H0Z',
        },
        rect: {
          strokeWidth: 0.5,
          stroke: '#DEE0E3',
          fill: '#F5F6F7',
          refY: 5,
        },
        div: {
          fillRule: 'evenodd',
          clipRule: 'evenodd',
          fill: '#646A73',
          refX: 12,
          refY: 21,
          fontSize: 14,
          d: 'M1.4773 1.47724C1.67618 1.27836 1.94592 1.16663 2.22719 1.16663H11.7729C12.0541 1.16663 12.3239 1.27836 12.5227 1.47724C12.7216 1.67612 12.8334 1.94586 12.8334 2.22713V11.7728C12.8334 12.0541 12.7216 12.3238 12.5227 12.5227C12.3239 12.7216 12.0541 12.8333 11.7729 12.8333H2.22719C1.64152 12.8333 1.16669 12.3585 1.16669 11.7728V2.22713C1.16669 1.94586 1.27842 1.67612 1.4773 1.47724ZM2.33335 5.83329V8.16662H4.66669V5.83329H2.33335ZM2.33335 9.33329V11.6666H4.66669V9.33329H2.33335ZM5.83335 11.6666H8.16669V9.33329H5.83335V11.6666ZM9.33335 11.6666H11.6667V9.33329H9.33335V11.6666ZM11.6667 8.16662V5.83329H9.33335V8.16662H11.6667ZM8.16669 5.83329H5.83335V8.16662H8.16669V5.83329ZM11.6667 2.33329H2.33335V4.66663H11.6667V2.33329Z',
        },
        label: {
          fill: '#1F2329',
          fontSize: 14,
        },
        labelComment: {
          fill: '#646A73',
          fontSize: 11,
        },
      },
      ports: {
        groups: {
          list: {
            markup: [
              { tagName: 'rect', selector: 'portBody' },
              { tagName: 'text', selector: 'portNameLabel' },
              { tagName: 'text', selector: 'portCommentLabel' },
            ],
            attrs: {
              portBody: {
                width: NODE_WIDTH,
                height: PORT_ROW_H,
                stroke: '#DEE0E3',
                strokeWidth: 0.5,
                fill: '#ffffff',
                magnet: true,
              },
              portNameLabel: {
                ref: 'portBody',
                refX: 12,
                refY: 11,
                fontSize: 13,
                fill: '#1F2329',
                textAnchor: 'left',
                textWrap: {
                  width: 148,
                  height: 18,
                  ellipsis: true,
                },
              },
              portCommentLabel: {
                ref: 'portBody',
                refX: 12,
                refY: 30,
                fontSize: 11,
                fill: '#909399',
                textAnchor: 'left',
                textWrap: {
                  width: 138,
                  height: 14,
                  ellipsis: true,
                },
              },
            },
            position: 'erPortPosition',
          },
        },
      },
    },
    true
  )
  graph = new Graph({
    mousewheel: {
      enabled: true,
      factor: 1.1,
    },
    scaling: {
      min: 0.2,
      max: 2,
    },
    container: document.getElementById('container')!,
    autoResize: true,
    panning: true,
    connecting: {
      allowBlank: false,
      router: {
        name: 'er',
        args: {
          offset: 25,
          direction: 'H',
        },
      },
      validateEdge({ edge }: any) {
        const obj = edge.store.data
        if (!obj.target.port || obj.target.cell === obj.source.cell) return false
        return true
      },
      createEdge() {
        return new Shape.Edge(edgeOPtion)
      },
    },
  })

  graph.on('edge:connected', () => refreshPortsDebounced())
  graph.on('edge:removed', () => refreshPortsDebounced())

  graph.on('edge:mouseenter', ({ e }: any) => {
    Array.from(document.querySelectorAll('.x6-edge-tool')).forEach((ele: any) => {
      if (ele.dataset.cellId === e.target.parentNode.dataset.cellId) {
        ele.style.display = 'block'
      }
    })
  })

  graph.on('edge:mouseleave', ({ e }: any) => {
    Array.from(document.querySelectorAll('.x6-edge-tool')).forEach((ele: any) => {
      if (ele.dataset.cellId === e.target.parentNode.dataset.cellId) {
        ele.style.display = 'none'
      }
    })
  })

  graph.on(
    'node:port:mouseenter',
    debounce(({ e, node, port }: any) => {
      tooltipY.value = e.offsetY + 'px'
      tooltipX.value = e.offsetX + 'px'
      const p = node.port?.ports?.find((x: any) => String(x.id) === String(port))
      const name = p?.attrs?.portNameLabel?.text || ''
      const c = p?.attrs?.portCommentLabel?.text || ''
      tooltipContent.value = c ? `${name}\n${c}` : name
    }, 100)
  )

  graph.on(
    'cell:mouseover',
    debounce(({ e, cell }: any) => {
      if (cell.store.data.shape === 'edge') return
      tooltipY.value = e.offsetY + 'px'
      tooltipX.value = e.offsetX + 'px'
      const name = cell.attr?.('label/text') ?? cell.store.data.attrs?.label?.text ?? ''
      const sub =
        cell.attr?.('labelComment/text') ?? cell.store.data.attrs?.labelComment?.text ?? ''
      tooltipContent.value = sub ? `${name}\n${sub}` : String(name)
    }, 100)
  )

  graph.on(
    'node:mouseleave',
    debounce(() => {
      resetTooltip()
    }, 100)
  )

  graph.on('node:click', ({ node, e, view }: any) => {
    if (view.findMagnet?.(e.target)) return
    const meta = tableMetaCache.get(String(node.id))
    emits('openTableDetail', { id: node.id, ...meta })
  })

  graph.on('node:mouseenter', ({ node }: any) => {
    node.addTools({
      name: 'button',
      args: {
        markup: [
          {
            tagName: 'circle',
            selector: 'button',
            attrs: {
              r: 7,
              cursor: 'pointer',
            },
          },
          {
            tagName: 'path',
            selector: 'icon',
            attrs: {
              d: 'M -3 -3 3 3 M -3 3 3 -3',
              stroke: 'white',
              'stroke-width': 2,
              cursor: 'pointer',
            },
          },
        ],
        x: 0,
        y: 0,
        offset: { x: 165, y: 38 },
        onClick({ view }: any) {
          node.removeTools()
          graph.removeNode(view.cell.id)
          const sid = String(view.cell.id)
          nodeIds.value = nodeIds.value.filter((ele) => String(ele) !== sid)
          fullFieldsCache.delete(sid)
          tableMetaCache.delete(sid)
          resetTooltip()
          if (!nodeIds.value.length) {
            graph.dispose()
            graph = null
          }
          emits('getTableName', [...nodeIds.value])
        },
      },
    })
  })

  graph.on('node:mouseleave', ({ node }: any) => {
    node.removeTools()
  })
}

const getTableData = () => {
  loading.value = true
  datasourceApi
    .relationGet(props.id)
    .then((data: any) => {
      if (!data.length) return
      nodeIds.value = data.filter((ele: any) => ele.shape === 'er-rect').map((ele: any) => ele.id)
      nextTick(async () => {
        fullFieldsCache.clear()
        tableMetaCache.clear()
        cells.value = []
        if (!graph) {
          initGraph()
        }
        const merged = preprocessLoadedCells(data)
        merged.forEach((item: any) => {
          if (item.shape === 'edge') {
            cells.value.push(graph.createEdge({ ...item, ...edgeOPtion }))
          } else {
            cells.value.push(
              graph.createNode({
                ...item,
                position: {
                  x: Number.parseInt(String(item.position?.x ?? 0), 10),
                  y: Number.parseInt(String(item.position?.y ?? 0), 10),
                },
              })
            )
          }
        })
        graph.resetCells(cells.value)
        graph.zoomToFit({ padding: 100 })
        emits('getTableName', [...nodeIds.value])
        await hydrateCanvasCommentsFromApi()
      })
    })
    .finally(() => {
      loading.value = false
    })
}

watch(showAllFields, () => {
  if (graph) refreshPortsOnGraph()
})

onMounted(() => {
  getTableData()
})
onBeforeUnmount(() => {
  graph = null
  fullFieldsCache.clear()
  tableMetaCache.clear()
})

const dragover = () => {
  // do
}

const addNode = (node: any, tableX: any, tableY: any) => {
  if (!graph) {
    initGraph()
  }
  const { x, y } = graph.pageToLocal(tableX, tableY)
  addNodeAt(node, x, y)
}

const addNodeAt = (node: any, x: number, y: number) => {
  if (!graph) {
    initGraph()
  }
  graph.addNode(
    graph.createNode({
      ...node,
      position: { x, y },
      width: NODE_WIDTH,
      height: node.height ?? getNodeHeightForPortCount(node.ports?.items?.length ?? node.ports?.length ?? 0),
    })
  )
}

const clickTable = (table: any) => {
  loading.value = true
  datasourceApi
    .fieldList(table.id)
    .then((res: unknown) => {
      const cfg = buildNodePayload(table, res as any[])
      nodeIds.value = [...nodeIds.value, table.id]
      nextTick(() => {
        addNode(cfg, table.x, table.y)
      })
      emits('getTableName', [...nodeIds.value])
    })
    .finally(() => {
      loading.value = false
    })
}

const drop = (e: any) => {
  const obj = JSON.parse(e.dataTransfer.getData('table') || '{}')
  if (!obj.id) return
  clickTable({
    ...obj,
    x: e.pageX,
    y: e.pageY,
  })
}

const save = () => {
  if (!graph) return
  const raw = graph.toJSON()
  const out = raw.cells.map((cell: any) => {
    if (cell.shape === 'er-rect') {
      const id = String(cell.id)
      const full = fullFieldsCache.get(id)
      if (full?.length) {
        const items = fieldsToPortItems(full)
        const mergedPorts =
          cell.ports && typeof cell.ports === 'object' && !Array.isArray(cell.ports)
            ? { ...cell.ports, items }
            : { items }
        return {
          ...cell,
          ports: mergedPorts,
          width: NODE_WIDTH,
          height: getNodeHeightForPortCount(items.length),
        }
      }
    }
    return cell
  })
  datasourceApi.relationSave(props.id, out).then(() => {
    ElMessage({
      type: 'success',
      message: t('common.save_success'),
    })
  })
}

const inferring = ref(false)
const addingAll = ref(false)

const buildNodeFromTable = (table: any, fields: any[]) => buildNodePayload(table, fields)

const addAllTables = async (tables: any[]) => {
  if (!tables?.length) return
  const idSet = new Set(nodeIds.value.map(String))
  const toAdd = tables.filter((t) => !idSet.has(String(t.id)))
  if (!toAdd.length) return
  addingAll.value = true
  try {
    await nextTick()
    if (!graph) {
      initGraph()
    }
    const results = await Promise.all(
      toAdd.map((t) => datasourceApi.fieldList(t.id).then((res) => ({ table: t, fields: res })))
    )
    const failed: string[] = []
    const nodes: { node: any; x: number; y: number }[] = []
    results.forEach((r) => {
      if (!r || !Array.isArray(r.fields)) {
        failed.push(r?.table?.table_name || '?')
        return
      }
      const node = buildNodeFromTable(r.table, r.fields)
      const i = nodeIds.value.length + nodes.length
      const x = (i % GRID_COLS) * GRID_STEP_X
      const y = Math.floor(i / GRID_COLS) * GRID_STEP_Y
      nodes.push({ node, x, y })
    })
    await nextTick()
    nodes.forEach(({ node, x, y }) => {
      addNodeAt(node, x, y)
      nodeIds.value = [...nodeIds.value, node.id]
    })
    emits('getTableName', [...nodeIds.value])
    await nextTick()
    gridAutoLayout()
    if (failed.length) {
      ElMessage.warning(t('training.add_all_partial_failed', { count: failed.length }))
    } else {
      ElMessage.success(t('training.add_all_success', { count: nodes.length }))
    }
  } catch (_e) {
    ElMessage.error(t('training.add_all_failed'))
  } finally {
    addingAll.value = false
  }
}

const zoomIn = () => {
  if (graph) graph.zoom(0.1)
}
const zoomOut = () => {
  if (graph) graph.zoom(-0.1)
}
const zoomToFit = () => {
  if (graph) graph.zoomToFit({ padding: 80 })
}
const zoomReset = () => {
  if (graph) graph.zoomTo(1)
}

const gridAutoLayout = () => {
  if (!graph) return
  const nodes = graph.getNodes()
  if (!nodes.length) return
  const sorted = [...nodes].sort((a, b) => {
    const idA = Number(a.id) || String(a.id)
    const idB = Number(b.id) || String(b.id)
    return idA < idB ? -1 : idA > idB ? 1 : 0
  })
  let currentY = 0
  for (let rowStart = 0; rowStart < sorted.length; rowStart += GRID_COLS) {
    const rowNodes = sorted.slice(rowStart, rowStart + GRID_COLS)
    const rowHeight =
      Math.max(...rowNodes.map((n) => getNodeHeight(n)), FIRST_PORT_Y) + LAYOUT_GAP_Y
    rowNodes.forEach((node, col) => {
      node.setPosition({ x: col * GRID_STEP_X, y: currentY })
    })
    currentY += rowHeight
  }
  nextTick(() => graph.zoomToFit({ padding: 80 }))
}

const inferRelations = () => {
  if (!graph || !nodeIds.value.length) {
    ElMessage.warning(t('training.infer_relations_no_tables'))
    return
  }
  inferring.value = true
  datasourceApi
    .relationInfer(props.id, nodeIds.value)
    .then((edges: any) => {
      if (!Array.isArray(edges) || !edges.length) {
        ElMessage.info(t('training.infer_relations_none'))
        return
      }
      const idSet = new Set(nodeIds.value.map(String))
      const existing = new Set(
        graph.getEdges().map((e: any) => {
          const s = e.getSource()
          const t = e.getTarget()
          return `${s?.cell}-${s?.port}-${t?.cell}-${t?.port}`
        })
      )
      let added = 0
      edges.forEach((item: any) => {
        const src = item.source?.cell != null ? String(item.source.cell) : null
        const tgt = item.target?.cell != null ? String(item.target.cell) : null
        if (!src || !tgt || !idSet.has(src) || !idSet.has(tgt)) return
        const key = `${src}-${item.source?.port}-${tgt}-${item.target?.port}`
        if (existing.has(key)) return
        existing.add(key)
        graph.addEdge(graph.createEdge({ ...item, ...edgeOPtion }))
        added++
      })
      if (added > 0) {
        ElMessage.success(t('training.infer_relations_success', { count: added }))
        nextTick(() => {
          refreshPortsOnGraph()
          gridAutoLayout()
        })
      } else {
        ElMessage.info(t('training.infer_relations_none'))
      }
    })
    .catch(() => {
      ElMessage.error(t('training.infer_relations_failed'))
    })
    .finally(() => {
      inferring.value = false
    })
}

defineExpose({ inferRelations, addAllTables })
</script>

<template>
  <svg style="position: fixed; top: -9999px" xmlns:xlink="http://www.w3.org/1999/xlink">
    <defs>
      <filter
        id="filter-dropShadow-v0-3329848037"
        x="-1"
        y="-1"
        width="3"
        height="3"
        filterUnits="objectBoundingBox"
      >
        <feDropShadow
          stdDeviation="4"
          dx="1"
          dy="2"
          flood-color="#1F23291F"
          flood-opacity="0.65"
        />
      </filter>
    </defs>
  </svg>
  <div
    v-if="!nodeIds.length && !addingAll"
    v-loading="loading"
    class="relationship-empty"
  >
    {{ t('training.add_it_here') }}
  </div>
  <div
    v-else
    class="relationship-canvas-wrap"
    v-loading="inferring"
    :element-loading-text="t('training.infer_relations_loading')"
  >
    <div class="canvas-toolbar">
      <el-button-group>
        <el-tooltip :content="t('training.canvas_zoom_in')" placement="bottom">
          <el-button size="small" secondary @click="zoomIn">
            <el-icon><Plus /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip :content="t('training.canvas_zoom_out')" placement="bottom">
          <el-button size="small" secondary @click="zoomOut">
            <el-icon><Minus /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip :content="t('training.canvas_zoom_fit')" placement="bottom">
          <el-button size="small" secondary @click="zoomToFit">
            {{ t('training.canvas_zoom_fit') }}
          </el-button>
        </el-tooltip>
        <el-tooltip :content="t('training.canvas_zoom_reset')" placement="bottom">
          <el-button size="small" secondary @click="zoomReset">100%</el-button>
        </el-tooltip>
      </el-button-group>
      <el-tooltip :content="t('training.canvas_layout_grid')" placement="bottom">
        <el-button size="small" secondary @click="gridAutoLayout">
          {{ t('training.canvas_layout_grid') }}
        </el-button>
      </el-tooltip>
      <el-tooltip :content="t('training.canvas_layout_dagre')" placement="bottom">
        <el-button size="small" secondary @click="runDagreLayout">
          {{ t('training.canvas_layout_dagre') }}
        </el-button>
      </el-tooltip>
      <el-tooltip :content="t('training.canvas_layout_force')" placement="bottom">
        <el-button size="small" secondary @click="runForceLayout">
          {{ t('training.canvas_layout_force') }}
        </el-button>
      </el-tooltip>
      <el-tooltip :content="t('training.canvas_layout_radial_tip')" placement="bottom">
        <el-button size="small" secondary @click="runRadialLayout">
          {{ t('training.canvas_layout_radial') }}
        </el-button>
      </el-tooltip>
      <span class="toolbar-switch">
        <el-switch v-model="showAllFields" size="small" />
        <span class="switch-label">{{ t('training.show_all_fields') }}</span>
      </span>
    </div>
    <div
      id="container"
      v-loading="loading || addingAll"
      :element-loading-text="addingAll ? t('training.adding_tables') : undefined"
    />
  </div>
  <div
    v-show="dragging"
    class="drag-mask"
    @dragover.prevent.stop="dragover"
    @drop.prevent.stop="drop"
  />
  <div class="save-btn">
    <el-button
      v-if="nodeIds.length"
      :loading="inferring"
      secondary
      style="margin-right: 8px"
      @click="inferRelations"
    >
      {{ t('training.infer_relations_short') }}
    </el-button>
    <el-button v-if="nodeIds.length" type="primary" @click="save">
      {{ t('common.save') }}
    </el-button>
  </div>
  <div class="tooltip-content" :style="{ top: tooltipY, left: tooltipX, position: 'absolute' }">
    {{ tooltipContent }}
  </div>
</template>

<style lang="less" scoped>
.tooltip-content {
  font-weight: 400;
  direction: ltr;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  outline: none;
  border-radius: 4px;
  padding: 5px 11px;
  font-size: 12px;
  line-height: 20px;
  min-width: 10px;
  max-width: 320px;
  overflow-wrap: break-word;
  word-break: normal;
  white-space: pre-wrap;
  visibility: visible;
  color: #fff;
  background: #303133;
  border: 1px solid #303133;
  transform: translate(20px, -15px);
  z-index: 20;
}
.toolbar-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-left: 4px;
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.switch-label {
  white-space: nowrap;
}
.relationship-canvas-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
}
.canvas-toolbar {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.relationship-canvas-wrap #container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  font-size: 14px;
  user-select: text;
  overflow: hidden;
  outline: none;
  touch-action: none;
  box-sizing: border-box;
  min-width: 400px;
  min-height: 400px;
  background-color: #f5f6f7;
  :deep(.x6-edge-tool) {
    display: none;
    circle {
      fill: var(--ed-color-primary) !important;
    }
  }
  :deep(.x6-node-tool) {
    circle {
      fill: var(--ed-color-primary) !important;
    }
  }
  :deep(.x6-node) {
    filter: url(#filter-dropShadow-v0-3329848037);
  }
}
.save-btn {
  position: absolute;
  right: 16px;
  bottom: 16px;
}
.drag-mask {
  width: 100%;
  height: 100%;
  position: absolute;
  left: 0;
  top: 56px;
  z-index: 10;
}
.relationship-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 16px;
}
</style>
