"""把主题排版转成大鱼号保存接口和预览均能保留的 HTML 表现属性。"""
from patchright.async_api import Page


async def render_dayu_compatible_html(page: Page, html: str, images: list[str]) -> dict:
    """保留文字和图片顺序，以 font/table 属性表达颜色、背景和近似字号，不把正文转成图片。"""
    return await page.evaluate("""({html, images}) => {
        const root = document.createElement('div'); root.innerHTML = html;
        const sourceImages = root.querySelectorAll('img');
        if (sourceImages.length !== images.length) throw Error('主题原稿与上传图片数量不符');
        const uploaded = images.map(html => {
            const holder = document.createElement('div'); holder.innerHTML = html;
            const image = holder.firstElementChild;
            if (image?.tagName !== 'IMG' || image.dataset.infoed !== '1') throw Error('图片缺少平台上传元数据');
            return image;
        });
        // 用浏览器解析颜色并合成透明色；旧式 color/bgcolor 属性只能表达不透明 RGB。
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
        const context = canvas.getContext('2d');
        function color(value, background) {
            context.clearRect(0, 0, 1, 1); context.fillStyle = value; context.fillRect(0, 0, 1, 1);
            const rgba = context.getImageData(0, 0, 1, 1).data;
            const rgb = [...rgba].slice(0, 3).map((n, i) => Math.round(n * rgba[3] / 255 + background[i] * (1 - rgba[3] / 255)));
            return {rgb, hex: '#' + rgb.map(n => n.toString(16).padStart(2, '0')).join(''), css: `rgb(${rgb.join(', ')})`};
        }
        function pixels(value, parent) {
            if (!value || value === 'inherit') return parent;
            // 渲染器的 calc(1.2 * 16px) 经浏览器解析后为 calc(19.2px)；保留其确定的像素值。
            const calculated = value.match(/^calc\\(([+-]?[\\d.]+)px\\)$/);
            if (calculated) return Number(calculated[1]);
            const n = parseFloat(value);
            if (!Number.isFinite(n)) throw Error(`不支持的主题尺寸: ${value}`);
            if (value.endsWith('rem')) return n * 16;
            if (value.endsWith('em')) return n * parent;
            if (value.endsWith('%')) return n * parent / 100;
            return n;
        }
        const fontSizes = [10, 13, 16, 18, 24, 32, 48];
        function borderPixels(value) {
            // Chromium 的边框关键字对应 1/3/5px；none/hidden 在调用处按不可见边框处理。
            const keywords = {thin: 1, medium: 3, thick: 5};
            return value in keywords ? keywords[value] : pixels(value || '0px', 0);
        }
        let imageIndex = 0;
        function visit(node, inherited) {
            if (node.nodeType === Node.TEXT_NODE) {
                if (!node.nodeValue.trim()) return document.createTextNode(node.nodeValue);
                const font = document.createElement('font'); font.textContent = node.nodeValue;
                const foreground = color(inherited.color, inherited.background);
                font.setAttribute('color', foreground.hex);
                font.setAttribute('face', inherited.fontFamily);
                let nearest = 0;
                fontSizes.forEach((size, i) => {
                    if (Math.abs(size - inherited.fontSize) < Math.abs(fontSizes[nearest] - inherited.fontSize)) nearest = i;
                });
                font.setAttribute('size', String(nearest + 1));
                return font;
            }
            if (node.nodeType !== Node.ELEMENT_NODE) return document.createTextNode('');
            const style = node.style;
            const backgroundValue = style.backgroundColor;
            const background = backgroundValue && backgroundValue !== 'transparent'
                ? color(backgroundValue, inherited.background) : null;
            const state = {
                color: style.color || inherited.color,
                background: background ? background.rgb : inherited.background,
                fontFamily: style.fontFamily || inherited.fontFamily,
                fontSize: pixels(style.fontSize, inherited.fontSize),
                align: style.textAlign || inherited.align,
            };
            if (node.tagName === 'IMG') {
                const image = uploaded[imageIndex++].cloneNode(true);
                for (const name of ['alt', 'title']) if (node.hasAttribute(name)) image.setAttribute(name, node.getAttribute(name));
                return image;
            }
            // 主题容器改用 div，避免平台把 section 变成含块级内容的 span；语义标题/引用/列表仍保留。
            const tag = ['SECTION', 'FIGURE'].includes(node.tagName) ? 'div' : node.tagName.toLowerCase();
            const element = document.createElement(tag);
            for (const attr of node.attributes) {
                if (!['style', 'id', 'class'].includes(attr.name)) element.setAttribute(attr.name, attr.value);
            }
            if (['left', 'center', 'right', 'justify'].includes(state.align)) element.setAttribute('align', state.align);
            for (const child of node.childNodes) element.appendChild(visit(child, state));
            if (tag === 'hr') {
                const visible = ['Top', 'Right', 'Bottom', 'Left'].filter(side =>
                    style[`border${side}Style`] && !['none', 'hidden'].includes(style[`border${side}Style`]));
                if (visible.length) element.setAttribute('color', color(style[`border${visible[0]}Color`], state.background).hex);
                element.setAttribute('size', String(Math.max(1, ...visible.map(side => borderPixels(style[`border${side}Width`])))));
                return element;
            }
            const sides = ['Top', 'Right', 'Bottom', 'Left'];
            const borders = sides.map(side => ({
                side, width: ['none', 'hidden', ''].includes(style[`border${side}Style`]) ? 0 : borderPixels(style[`border${side}Width`]),
                color: style[`border${side}Color`],
            })).filter(border => border.width > 0);
            const padding = Math.max(...sides.map(side => pixels(style[`padding${side}`] || '0px', state.fontSize)));
            if (!background && !borders.length && !padding) return element;
            // 实测保存及预览保留这些 table 属性；不依赖会被移除的 CSS，也不伪造平台图片标记。
            const table = document.createElement('table');
            table.setAttribute('width', '100%'); table.setAttribute('cellspacing', '0');
            table.setAttribute('cellpadding', String(Math.round(padding)));
            table.setAttribute('border', borders.length ? String(Math.round(borders[0].width)) : '0');
            if (background) table.setAttribute('bgcolor', background.hex);
            if (borders.length) {
                table.setAttribute('bordercolor', color(borders[0].color, state.background).hex);
                const frames = {Top: 'above', Bottom: 'below', Left: 'lhs', Right: 'rhs'};
                table.setAttribute('frame', borders.length === 1 ? frames[borders[0].side] : 'box');
                table.setAttribute('rules', 'none');
            }
            const row = table.insertRow(), cell = row.insertCell();
            cell.setAttribute('valign', 'top'); cell.appendChild(element);
            return table;
        }
        const output = document.createElement('div');
        const defaults = {color: '#333333', background: [255, 255, 255], fontFamily: 'Microsoft YaHei, sans-serif', fontSize: 16, align: 'left'};
        for (const child of root.childNodes) output.appendChild(visit(child, defaults));
        const textColors = [...output.querySelectorAll('font[color]')].map(font => ({
            text: font.textContent.replace(/[\\s\\u200b\\ufeff]+/g, ''),
            color: color(font.getAttribute('color'), [255, 255, 255]).css,
        }));
        const backgroundColors = [...output.querySelectorAll('table[bgcolor]')].map(table => color(table.getAttribute('bgcolor'), [255, 255, 255]).css);
        return {html: output.innerHTML, expectations: {text_colors: textColors, background_colors: backgroundColors},
                mode: 'dayu-compatible', limitations: ['圆角不保留', '字号映射为平台可保留的字体等级', '间距和边框可能与本地主题不同']};
    }""", {"html": html, "images": images})
