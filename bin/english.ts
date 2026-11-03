/**
 * English 启动器
 *
 * 用户视角只做一件事：敲 `english`，浏览器打开应用。
 * 背后按顺序完成：环境检查 → 首次引导 → 找端口 → 起 uvicorn → 等健康检查 → 开浏览器。
 */
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, unlinkSync } from 'node:fs'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(HERE, '..')
const WEB_DIR = path.join(ROOT, 'web')
const API_DIR = path.join(ROOT, 'api')
const SEED_SCRIPT = path.join(ROOT, 'scripts', 'import_ecdict.py')

const BASE_PORT = 8765
const IS_WIN = process.platform === 'win32'

const APP_HOME =
  process.env.ENGLISH_HOME ??
  (process.env.APPDATA
    ? path.join(process.env.APPDATA, 'english-app')
    : path.join(os.homedir(), '.english-app'))

const DB_FILE = path.join(APP_HOME, 'data', 'english.db')

const c = {
  dim: (s: string) => `\x1b[2m${s}\x1b[0m`,
  green: (s: string) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s: string) => `\x1b[33m${s}\x1b[0m`,
  red: (s: string) => `\x1b[31m${s}\x1b[0m`,
  cyan: (s: string) => `\x1b[36m${s}\x1b[0m`
}

const step = (n: number, total: number, text: string) =>
  console.log(`${c.cyan(`[${n}/${total}]`)} ${text}`)

/** shell:true 会直接拼字符串，带空格的参数（Program Files 这种）必须自己加引号 */
const quoteArg = (arg: string) => (IS_WIN && /\s/.test(arg) ? `"${arg}"` : arg)

/** 执行一条命令，失败时打印可读的错误并退出 */
function run(command: string, args: string[], cwd: string): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const child = spawn(command, args.map(quoteArg), {
      cwd,
      stdio: 'inherit',
      shell: IS_WIN,
      env: { ...process.env, ENGLISH_HOME: APP_HOME }
    })
    child.on('error', reject)
    child.on('exit', (code) => {
      if (code === 0) resolve()
      else reject(new Error(`${command} ${args.join(' ')} 退出码 ${code}`))
    })
  })
}

/** 命令是否存在 */
function has(command: string): boolean {
  const probe = IS_WIN ? 'where' : 'which'
  const r = spawnSync(probe, [command], { stdio: 'ignore', shell: IS_WIN })
  return r.status === 0
}

async function ensureUv(): Promise<void> {
  if (has('uv')) return
  console.log(c.yellow('未检测到 uv，正在为你安装（只需一次）…'))
  if (IS_WIN) {
    await run('powershell', [
      '-NoProfile',
      '-ExecutionPolicy', 'Bypass',
      '-Command',
      'irm https://astral.sh/uv/install.ps1 | iex'
    ], ROOT)
  } else {
    await run('sh', ['-c', 'curl -LsSf https://astral.sh/uv/install.sh | sh'], ROOT)
  }
  // 安装后当前进程的 PATH 还没刷新，补进常见位置
  const candidates = IS_WIN
    ? [path.join(os.homedir(), '.local', 'bin'), path.join(os.homedir(), '.cargo', 'bin')]
    : [path.join(os.homedir(), '.local', 'bin'), path.join(os.homedir(), '.cargo', 'bin')]
  for (const dir of candidates) {
    if (existsSync(dir) && !process.env.PATH?.includes(dir)) {
      process.env.PATH = `${dir}${path.delimiter}${process.env.PATH ?? ''}`
    }
  }
  if (!has('uv')) {
    throw new Error('uv 安装后仍找不到，请关闭终端重新打开，再运行一次 english')
  }
}

async function bootstrap(): Promise<void> {
  const total = 5
  console.log('')
  console.log(c.green('  首次启动，需要几分钟准备环境。之后每次启动都是秒开。'))
  console.log('')

  step(1, total, '准备 Python 运行时')
  await ensureUv()
  try {
    await run('uv', ['python', 'install', '3.12'], API_DIR)
  } catch {
    console.log(c.dim('  Python 3.12 已存在，跳过'))
  }

  step(2, total, '安装后端依赖（uv sync）')
  await run('uv', ['sync'], API_DIR)

  step(3, total, '构建前端')
  if (!existsSync(path.join(WEB_DIR, 'node_modules'))) {
    await run('npm', ['install'], WEB_DIR)
  }
  await run('npm', ['run', 'build'], WEB_DIR)

  step(4, total, '导入词库')
  if (!existsSync(DB_FILE) || process.env.ENGLISH_FORCE_SEED === '1') {
    await run('uv', ['run', 'python', SEED_SCRIPT], API_DIR)
  } else {
    console.log(c.dim('  词库已存在，跳过（要重建请设 ENGLISH_FORCE_SEED=1）'))
  }

  step(5, total, '完成')
}

function isPortFree(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', () => resolve(false))
    server.once('listening', () => server.close(() => resolve(true)))
    server.listen(port, '127.0.0.1')
  })
}

async function pickPort(): Promise<number> {
  for (let port = BASE_PORT; port < BASE_PORT + 20; port++) {
    if (await isPortFree(port)) return port
  }
  throw new Error(`从 ${BASE_PORT} 起的 20 个端口都被占用了，请先关掉占用它们的程序`)
}

async function waitForHealth(url: string, timeoutMs = 90_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url)
      if (res.ok) return
    } catch {
      /* 还没起来，继续等 */
    }
    await new Promise((r) => setTimeout(r, 300))
  }
  throw new Error('后端启动超时，可以到 %APPDATA%\\english-app\\logs 查看日志')
}

function openBrowser(url: string): void {
  if (process.env.ENGLISH_NO_OPEN === '1') return
  if (IS_WIN) {
    spawn('cmd', ['/c', 'start', '', url], { detached: true, stdio: 'ignore' }).unref()
  } else if (process.platform === 'darwin') {
    spawn('open', [url], { detached: true, stdio: 'ignore' }).unref()
  } else {
    spawn('xdg-open', [url], { detached: true, stdio: 'ignore' }).unref()
  }
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2)
  if (argv.includes('--help') || argv.includes('-h')) {
    console.log(`
  用法: english [选项]

    --no-open     启动但不自动打开浏览器
    --reset       删除本地数据库后重新导入词库
    --help        显示这段帮助

  数据目录: ${APP_HOME}
`)
    return
  }
  if (argv.includes('--reset')) {
    // 真正删掉数据库，否则导入脚本会跳过已存在的词条，等于没重置
    if (existsSync(DB_FILE)) {
      unlinkSync(DB_FILE)
      console.log(c.yellow('已删除本地数据库，下次启动会重新导入词库'))
    }
    process.env.ENGLISH_FORCE_SEED = '1'
  }

  mkdirSync(path.join(APP_HOME, 'data'), { recursive: true })
  mkdirSync(path.join(APP_HOME, 'logs'), { recursive: true })
  mkdirSync(path.join(APP_HOME, 'uploads'), { recursive: true })

  const needsBootstrap =
    !existsSync(path.join(API_DIR, '.venv')) ||
    !existsSync(path.join(WEB_DIR, 'dist')) ||
    !existsSync(DB_FILE)

  if (needsBootstrap) {
    await bootstrap()
  } else if (!existsSync(path.join(ROOT, 'dist', 'bin.js'))) {
    // 用 npm link 之后 bin.js 丢了，不影响运行，只是提示一下
    console.log(c.dim('提示：启动器还没有编译产物，这不影响使用'))
  }

  const port = await pickPort()
  const url = `http://127.0.0.1:${port}`

  console.log('')
  console.log(c.dim('  正在启动服务…'))
  const server = spawn(
    'uv',
    ['run', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)],
    {
      cwd: API_DIR,
      stdio: ['ignore', 'inherit', 'inherit'],
      shell: IS_WIN,
      env: { ...process.env, ENGLISH_HOME: APP_HOME, ENGLISH_PORT: String(port) }
    }
  )

  const shutdown = () => {
    if (server.pid) {
      if (IS_WIN) {
        // Windows 上只杀父进程会留下占着端口的孤儿，必须杀整棵树
        spawnSync('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' })
      } else {
        server.kill('SIGINT')
      }
    }
    process.exit(0)
  }
  process.on('SIGINT', shutdown)
  process.on('SIGTERM', shutdown)
  server.on('exit', (code) => {
    if (code !== 0 && code !== null) {
      console.error(c.red(`\n服务异常退出（code ${code}）`))
    }
    process.exit(code ?? 0)
  })

  try {
    await waitForHealth(`${url}/api/health`)
  } catch (err) {
    console.error(c.red(`\n${(err as Error).message}`))
    shutdown()
    return
  }

  console.log('')
  console.log(c.green(`  ✓ English 已启动  ${url}`))
  console.log(c.dim('    按 Ctrl+C 退出'))
  console.log('')
  openBrowser(url)
}

main().catch((err) => {
  console.error('')
  console.error(c.red(`启动失败：${(err as Error).message}`))
  console.error(c.dim('如果反复失败，把上面的报错发我，或先手动执行 npm run dev 排查'))
  process.exit(1)
})
