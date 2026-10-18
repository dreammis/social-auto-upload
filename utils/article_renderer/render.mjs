/** 只执行本地 Markdown 渲染；stdin/stdout 使用 JSON，正文不经过命令行参数。 */
import { renderMarkdownDocument, resolveMarkdownStyle } from 'baoyu-md';
import { Marked } from 'marked';
import { load } from 'cheerio';

let input = '';
// 按字符解码流，避免长中文稿跨 Buffer 边界时出现替换字符。
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) input += chunk;
try {
  const { content, theme } = JSON.parse(input);
  const markdown = new Marked({ gfm: true });
  // 图表扩展会产生 SVG 或远程图片，不作为普通代码块静默降级。
  const tokens = markdown.lexer(content);
  markdown.walkTokens(tokens, token => {
    if (token.type === 'html' && /<\/?(?:script|style|link|iframe|object|embed)\b/i.test(token.raw)) {
      throw Error('Markdown 内嵌 HTML 不支持脚本、外部资源或样式表，请使用内联样式');
    }
    if (token.type === 'code' && /^(mermaid|plantuml|infographic)(\s|$)/i.test(token.lang || '')) {
      throw Error(`暂不支持 ${token.lang} 图表，请先导出为本地图片`);
    }
  });
  if (theme === 'plain') {
    process.stdout.write(JSON.stringify({ html: markdown.parser(tokens), metadata: {} }));
  } else {
    // 显式给出全部选项，避免上游读取用户的 EXTEND.md 后改变本项目的默认排版。
    const style = resolveMarkdownStyle({ theme });
    const result = await renderMarkdownDocument(content, {
      theme, primaryColor: style.primaryColor, fontFamily: style.fontFamily,
      fontSize: style.fontSize, codeTheme: 'github', countStatus: false,
      citeStatus: false, keepTitle: true, legend: 'none',
      isMacCodeBlock: false, isShowLineNumber: false, themeMode: 'light',
    });
    // 上游即使关闭 Mac 代码装饰也保留隐藏 SVG；只移除该装饰，不删除用户正文元素。
    const $ = load(result.html);
    $('pre.code__pre > span.mac-sign').remove();
    // 上游用正文里的“1. / • ”和 display:block 模拟列表；平台清理 CSS 后会显示双重序号。
    // 恢复原生列表语义，保留其余主题样式，使本地和过滤样式后的平台都只显示一次标记。
    $('ol,ul').each((_, list) => {
      const ordered = list.tagName === 'ol';
      $(list).children('li.listitem').each((index, item) => {
        const first = item.children[0];
        if (first?.type !== 'text') return;
        const prefix = first.data.match(ordered ? /^(\d+)\. / : /^• /);
        if (!prefix) return;
        if (ordered && index === 0 && Number(prefix[1]) !== 1) $(list).attr('start', prefix[1]);
        first.data = first.data.slice(prefix[0].length);
        $(item).attr('style', ($(item).attr('style') || '').replace(/display:\s*block\s*;/, 'display: list-item;'));
      });
    });
    process.stdout.write(JSON.stringify({ html: $.html(), metadata: result.meta }));
  }
} catch (error) {
  process.stderr.write(error.stack || String(error));
  process.exitCode = 1;
}
