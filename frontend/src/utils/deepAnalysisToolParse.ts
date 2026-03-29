/**
 * 解析深度分析里常见的 LangChain ToolMessage 风格字符串：
 * content='...' name='sqlbot_sync_datasource' tool_call_id='...'
 * 并从中拆分叙述文本、JSON、SQL（代码块与 JSON 字段）。
 */

const SQL_JSON_KEYS = [
  'sql',
  'query',
  'dialect_sql',
  'generated_sql',
  'dialect_template',
  'statement',
  'final_sql',
  'explain_sql',
  'sample_sql',
  'ddl',
  'create_sql',
  'template',
  'example_sql',
  'dialect_example',
  'snippet',
]

/** 与后端一致：仅在「引号后紧跟 name=」处结束，避免正文里未转义 ' 提前截断 */
function scanQuotedUntilNameField(s: string, start: number, q: string): string | null {
  let i = start
  const parts: string[] = []
  let esc = false
  const n = s.length
  while (i < n) {
    const c = s[i]
    if (esc) {
      if (c === 'n') parts.push('\n')
      else if (c === 't') parts.push('\t')
      else if (c === 'r') parts.push('\r')
      else if (c === q || c === '\\') parts.push(c)
      else {
        parts.push('\\')
        parts.push(c)
      }
      esc = false
      i++
      continue
    }
    if (c === '\\') {
      esc = true
      i++
      continue
    }
    if (c === q) {
      const tail = s.slice(i + 1, Math.min(n, i + 64))
      if (/^\s*name\s*=/.test(tail)) {
        return parts.join('')
      }
    }
    parts.push(c)
    i++
  }
  return null
}

/** 从 key= 后解析单引号或双引号包裹的字符串（支持 \\、\\n 等；content= 使用 name= 边界） */
export function extractQuotedField(s: string, key: string): string | null {
  const marker = `${key}=`
  let i = s.indexOf(marker)
  if (i < 0) return null
  i += marker.length
  if (i >= s.length) return null
  const q = s[i]
  if (q !== '"' && q !== "'") return null
  i++
  if (key === 'content') {
    return scanQuotedUntilNameField(s, i, q)
  }
  const parts: string[] = []
  let esc = false
  while (i < s.length) {
    const c = s[i]
    if (esc) {
      if (c === 'n') parts.push('\n')
      else if (c === 't') parts.push('\t')
      else if (c === 'r') parts.push('\r')
      else parts.push(c)
      esc = false
    } else if (c === '\\') {
      esc = true
    } else if (c === q) {
      break
    } else {
      parts.push(c)
    }
    i++
  }
  return parts.join('')
}

export function extractToolNameFromRepr(s: string): string | undefined {
  const m = s.match(/\bname\s*=\s*['"]([\w.-]+)['"]/)
  return m ? m[1] : undefined
}

/**
 * 若整段为 ToolMessage 风格，解包为真实正文与工具名；否则原文返回。
 */
export function unwrapToolMessageRepr(raw: string): { body: string; toolName?: string } {
  const t = raw.trim()
  if (!t.includes('content=') || !/\bname\s*=/.test(t)) {
    return { body: raw }
  }
  const inner = extractQuotedField(t, 'content')
  if (inner == null) return { body: raw }
  return {
    body: inner,
    toolName: extractToolNameFromRepr(t),
  }
}

/** 从第一个 { 起平衡括号截取 JSON 对象并解析 */
export function extractTrailingJsonObject(s: string): {
  before: string
  json: Record<string, unknown> | null
} {
  const start = s.indexOf('{')
  if (start < 0) return { before: s.trim(), json: null }

  let depth = 0
  let inStr = false
  let strQ = ''
  let esc = false

  for (let i = start; i < s.length; i++) {
    const c = s[i]
    if (inStr) {
      if (esc) {
        esc = false
      } else if (c === '\\') {
        esc = true
      } else if (c === strQ) {
        inStr = false
      }
      continue
    }
    if (c === '"' || c === "'") {
      inStr = true
      strQ = c
      continue
    }
    if (c === '{') depth++
    else if (c === '}') {
      depth--
      if (depth === 0) {
        const chunk = s.slice(start, i + 1)
        try {
          const json = JSON.parse(chunk) as Record<string, unknown>
          const before = s.slice(0, start).trim()
          return { before, json }
        } catch {
          return { before: s.trim(), json: null }
        }
      }
    }
  }
  return { before: s.trim(), json: null }
}

function keyLooksSqlRelated(key: string): boolean {
  const lk = key.toLowerCase()
  return SQL_JSON_KEYS.some((k) => lk === k || lk.endsWith(`_${k}`) || lk.startsWith(`${k}_`))
}

/** 递归从 JSON 中收集可能是 SQL 的字符串（按 key 名启发式） */
export function collectSqlStringsFromJson(
  obj: unknown,
  out: { sql: string; field: string }[],
  seen: Set<string>
): void {
  if (obj == null) return
  if (typeof obj === 'string') return
  if (Array.isArray(obj)) {
    obj.forEach((x) => collectSqlStringsFromJson(x, out, seen))
    return
  }
  if (typeof obj !== 'object') return

  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (typeof v === 'string' && v.trim().length > 12) {
      const t = v.trim()
      if (keyLooksSqlRelated(k)) {
        const templateLike = /template|dialect|example|snippet|tpl/i.test(k)
        const sqlLike =
          /^\s*(select|with|insert|update|delete|create|alter|explain|--|\/\*)/i.test(t) ||
          (templateLike && t.length > 20)
        if (sqlLike) {
          const norm = t.replace(/\s+/g, ' ')
          if (!seen.has(norm)) {
            seen.add(norm)
            out.push({ sql: v.trim(), field: k })
          }
        }
      }
    } else {
      collectSqlStringsFromJson(v, out, seen)
    }
  }
}

/** 去掉已匹配的 ```sql``` 块后剩余文本 */
export function stripSqlFences(s: string): { rest: string; fences: string[] } {
  const fences: string[] = []
  const re = /```sql\s*\n?([\s\S]*?)```/gi
  let rest = s
  let m: RegExpExecArray | null
  const matches: { full: string; inner: string }[] = []
  while ((m = re.exec(s)) !== null) {
    matches.push({ full: m[0], inner: m[1].trim() })
  }
  for (const x of matches) {
    fences.push(x.inner)
    rest = rest.replace(x.full, '\n')
  }
  return { rest: rest.replace(/\n{3,}/g, '\n\n').trim(), fences }
}

export interface ParsedToolBody {
  narrativeMd: string
  sqlFromFences: string[]
  sqlFromJson: { sql: string; field: string }[]
  jsonPretty: string | null
  toolName?: string
}

/**
 * 对工具输出正文（已 unwrap）做结构化拆分。
 */
export function parseToolBodyStructured(body: string, toolName?: string): ParsedToolBody {
  const { rest: afterFences, fences } = stripSqlFences(body)
  const { before, json } = extractTrailingJsonObject(afterFences)

  const sqlFromJsonRaw: { sql: string; field: string }[] = []
  if (json) {
    collectSqlStringsFromJson(json, sqlFromJsonRaw, new Set())
  }

  const fenceNorms = new Set(fences.map((x) => x.replace(/\s+/g, ' ')))
  const seenNorm = new Set<string>()
  const dedupedJsonSql: { sql: string; field: string }[] = []
  for (const x of sqlFromJsonRaw) {
    const norm = x.sql.replace(/\s+/g, ' ')
    if (seenNorm.has(norm) || fenceNorms.has(norm)) continue
    seenNorm.add(norm)
    dedupedJsonSql.push(x)
  }

  let jsonPretty: string | null = null
  if (json) {
    try {
      jsonPretty = JSON.stringify(json, null, 2)
    } catch {
      jsonPretty = null
    }
  }

  const narrativeMd = before.trim()

  return {
    narrativeMd,
    sqlFromFences: fences,
    sqlFromJson: dedupedJsonSql,
    jsonPretty,
    toolName,
  }
}
