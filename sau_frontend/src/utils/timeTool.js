/**
 * 2022.08.17 mouda
 * 时间工具盒
 * @method day 获取日期 num 范围 如1获取明天 -1获取昨天
 * @method week 获取周期 num 范围 如1获取下周 -1获取上周
 * @method month 获取月份 num 范围 如1获取下个月 -1获取上个月
 * @method year 获取年份 num 范围 如1获取下年 -1获取上年
 * @method laterDay XXX之后日期 num 范围 如10 获取10天后 如-10 获取10天前
 * @method dayRange 时间范围 s 开始天数 e 结束天数
 */
export function timeTools() {
	return {
		day: (num,newDate) => {
			const days = 1000 * 60 * 60 * 24 * num;
			const time = new Date(newDate ? newDate + days : new Date().getTime() + days);
			return time;
		},
		week: (num) => {
			let date = new Date();
			let one_day = 86400000;
			let day = date.getDay() - 7 * num;
			date.setHours(0);
			date.setMinutes(0);
			date.setSeconds(0);
			date.setMilliseconds(0);
			const week_start_time = new Date(date.getTime() - (day - 1) * one_day);
			const week_end_time = new Date(date.getTime() + (8 - day) * one_day - 1);
			return [week_start_time, week_end_time];
		},
		month: (num,newDate) => {
			let one_day = 86400000;
			let time = newDate ? new Date(newDate) : new Date();
			let date = new Date(time.getFullYear(), time.getMonth() + num + 1, 0);
			const month_start_time = new Date(date.setDate(1));
			const month_end_time = new Date(date.getFullYear(), date.getMonth() + 1, 0);
			return [month_start_time, new Date(month_end_time.getTime()+one_day-1)];
		},
		year: (num) => {
			let date = new Date();
			let one_day = 86400000;
			date.setFullYear(date.getFullYear() + num);
			date.setDate(1);
			date.setMonth(0);
			date.setHours(0);
			date.setMinutes(0);
			date.setSeconds(0);
			date.setMilliseconds(0);
			let lastDay = new Date();
			lastDay.setFullYear(lastDay.getFullYear() + num + 1);
			lastDay.setDate(0);
			lastDay.setMonth(-1);
			lastDay.setHours(0);
			lastDay.setMinutes(0);
			lastDay.setSeconds(0);
			lastDay.setMilliseconds(0);
			return [date, new Date(lastDay.getTime()+one_day*2-1)];
		},
		laterDay: (num,newDate) => {
			const day = newDate ? new Date(newDate) : new Date();
			day.setTime(day.getTime() - 3600 * 1000 * 24 * num);
			return day;
		},
		dayRange: (s, e) => {
			const start_days = 1000 * 60 * 60 * 24 * s;
			const end_days = 1000 * 60 * 60 * 24 * e;
			const start = new Date(new Date().getTime() + start_days);
			const end = new Date(new Date().getTime() + end_days);
			const start_time = new Date(start.setHours(0, 0, 0, 0));
			const end_time = new Date(end.setHours(0, 0, 0, 0) + 24 * 60 * 60 * 1000 - 1);
			return [start_time, end_time];
		},
	};
}

/**
 * 时间日期转换
 * @param date 当前时间，new Date() 格式
 * @param format 需要转换的时间格式字符串
 * @description format 字符串随意，如 `YYYY-mm、YYYY-mm-dd`
 * @description format 季度："YYYY-mm-dd HH:MM:SS QQQQ"
 * @description format 星期："YYYY-mm-dd HH:MM:SS WWW"
 * @description format 几周："YYYY-mm-dd HH:MM:SS ZZZ"
 * @description format 季度 + 星期 + 几周："YYYY-mm-dd HH:MM:SS WWW QQQQ ZZZ"
 * @returns 返回拼接后的时间字符串
 */
export function formatDate(date, format) {
	format = format ? format : 'YYYY-mm-dd HH:MM:SS';
	let we = date.getDay(); // 星期
	let z = getWeek(date); // 周
	let qut = Math.floor((date.getMonth() + 3) / 3).toString(); // 季度
	const opt = {
		'Y+': date.getFullYear().toString(), // 年
		'm+': (date.getMonth() + 1).toString(), // 月(月份从0开始，要+1)
		'd+': date.getDate().toString(), // 日
		'H+': date.getHours().toString(), // 时
		'M+': date.getMinutes().toString(), // 分
		'S+': date.getSeconds().toString(), // 秒
		'q+': qut, // 季度
	};
	// 中文数字 (星期)
	const week = {
		0: '日',
		1: '一',
		2: '二',
		3: '三',
		4: '四',
		5: '五',
		6: '六',
	};
	// 中文数字（季度）
	const quarter = {
		1: '一',
		2: '二',
		3: '三',
		4: '四',
	};
	if (/(W+)/.test(format))
		format = format.replace(RegExp.$1, RegExp.$1.length > 1 ? (RegExp.$1.length > 2 ? '星期' + week[we] : '周' + week[we]) : week[we]);
	if (/(Q+)/.test(format)) format = format.replace(RegExp.$1, RegExp.$1.length == 4 ? '第' + quarter[qut] + '季度' : quarter[qut]);
	if (/(Z+)/.test(format)) format = format.replace(RegExp.$1, RegExp.$1.length == 3 ? '第' + z + '周' : z + '');
	for (let k in opt) {
		let r = new RegExp('(' + k + ')').exec(format);
		// 若输入的长度不为1，则前面补零
		if (r) format = format.replace(r[1], RegExp.$1.length == 1 ? opt[k] : opt[k].padStart(RegExp.$1.length, '0'));
	}
	return format;
}

/**
 * 获取当前日期是第几周
 * @param dateTime 当前传入的日期值
 * @returns 返回第几周数字值
 */
export function getWeek(dateTime) {
	let temptTime = new Date(dateTime.getTime());
	// 周几
	let weekday = temptTime.getDay() || 7;
	// 周1+5天=周六
	temptTime.setDate(temptTime.getDate() - weekday + 1 + 5);
	let firstDay = new Date(temptTime.getFullYear(), 0, 1);
	let dayOfWeek = firstDay.getDay();
	let spendDay = 1;
	if (dayOfWeek != 0) spendDay = 7 - dayOfWeek + 1;
	firstDay = new Date(temptTime.getFullYear(), 0, 1 + spendDay);
	let d = Math.ceil((temptTime.valueOf() - firstDay.valueOf()) / 86400000);
	let result = Math.ceil(d / 7);
	return result;
}

/**
 * 将时间转换为 `几秒前`、`几分钟前`、`几小时前`、`几天前`
 * @param param 当前时间，new Date() 格式或者字符串时间格式
 * @param format 需要转换的时间格式字符串
 * @description param 10秒：  10 * 1000
 * @description param 1分：   60 * 1000
 * @description param 1小时： 60 * 60 * 1000
 * @description param 24小时：60 * 60 * 24 * 1000
 * @description param 3天：   60 * 60* 24 * 1000 * 3
 * @returns 返回拼接后的时间字符串
 */
export function formatPast(param, format) {
	// 传入格式处理、存储转换值
	let t, s;
	// 获取js 时间戳
	let time = new Date().getTime();
	// 是否是对象
	typeof param === 'string' || 'object' ? (t = new Date(param).getTime()) : (t = param);
	// 当前时间戳 - 传入时间戳
	time = Number.parseInt(`${time - t}`);
	if (time < 10000) {
		// 10秒内
		return '刚刚';
	} else if (time < 60000 && time >= 10000) {
		// 超过10秒少于1分钟内
		s = Math.floor(time / 1000);
		return `${s}秒前`;
	} else if (time < 3600000 && time >= 60000) {
		// 超过1分钟少于1小时
		s = Math.floor(time / 60000);
		return `${s}分钟前`;
	} else if (time < 86400000 && time >= 3600000) {
		// 超过1小时少于24小时
		s = Math.floor(time / 3600000);
		return `${s}小时前`;
	} else if (time < 259200000 && time >= 86400000) {
		// 超过1天少于3天内
		s = Math.floor(time / 86400000);
		return `${s}天前`;
	} else {
		// 超过3天
		let date = typeof param === 'string' || 'object' ? new Date(param) : param;
		return formatDate(date, format);
	}
}

/**
 * 时间问候语
 * @param param 当前时间，new Date() 格式
 * @description param 调用 `formatAxis(new Date())` 输出 `上午好`
 * @returns 返回拼接后的时间字符串
 */
export function formatAxis(param) {
	let hour = new Date(param).getHours();
	if (hour < 6) return '凌晨好';
	else if (hour < 9) return '早上好';
	else if (hour < 12) return '上午好';
	else if (hour < 14) return '中午好';
	else if (hour < 17) return '下午好';
	else if (hour < 19) return '傍晚好';
	else if (hour < 22) return '晚上好';
	else return '夜里好';
}