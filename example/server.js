#!/usr/bin/env node
/**
 * 静态文件服务，用于运行小助手嵌入示例
 * 使用方式：node server.js  或  PORT=8080 node server.js
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.PORT, 10) || 3000;
const ROOT = path.join(__dirname);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json',
  '.css': 'text/css',
  '.ico': 'image/x-icon',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.woff2': 'font/woff2',
};

const server = http.createServer((req, res) => {
  let filePath = path.join(ROOT, req.url === '/' ? 'index.html' : req.url);
  filePath = path.normalize(filePath);
  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.writeHead(404);
        res.end('Not Found');
      } else {
        res.writeHead(500);
        res.end('Server Error');
      }
      return;
    }
    const ext = path.extname(filePath);
    res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
    res.end(data);
  });
});

server.listen(PORT, () => {
  const url = `http://localhost:${PORT}`;
  console.log('');
  console.log('  小助手嵌入示例服务已启动');
  console.log('  访问地址: ' + url);
  console.log('');
  console.log('  请在 SQLBot「小助手应用」中将跨域设置包含: ' + url);
  console.log('');
});
