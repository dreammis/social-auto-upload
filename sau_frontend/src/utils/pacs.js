import { timeTools } from './timeTool';

/**
 * 通用js方法封装处理
 * Copyright (c) 2018 yangshi
 */

// 日期格式化
export function parseTime(time, pattern) {
    if (arguments.length === 0 || !time) {
        return null
    }
    const format = pattern || '{y}-{m}-{d} {h}:{i}:{s}'
    let date
    if (typeof time === 'object') {
        date = time
    } else {
        if ((typeof time === 'string') && (/^[0-9]+$/.test(time))) {
            time = parseInt(time)
        } else if (typeof time === 'string') {
            time = time.replace(new RegExp(/-/gm), '/').replace('T', ' ').replace(new RegExp(/\.[\d]{3}/gm), '');

            // 添加以下代码，将日期字符串转换为 ISO 8601 格式
            const offsetIndex = time.lastIndexOf('+');
            if (offsetIndex > -1) {
                time = time.substring(0, offsetIndex);
            }
            time = new Date(time).toISOString();
        }
        if ((typeof time === 'number') && (time.toString().length === 10)) {
            time = time * 1000
        }
        date = new Date(time)
    }
    const formatObj = {
        y: date.getFullYear(),
        m: date.getMonth() + 1,
        d: date.getDate(),
        h: date.getHours(),
        i: date.getMinutes(),
        s: date.getSeconds(),
        a: date.getDay()
    }
    const time_str = format.replace(/{(y|m|d|h|i|s|a)+}/g, (result, key) => {
        let value = formatObj[key]
        // Note: getDay() returns 0 on Sunday
        if (key === 'a') {
            return ['日', '一', '二', '三', '四', '五', '六'][value]
        }
        if (result.length > 0 && value < 10) {
            value = '0' + value
        }
        return value || 0
    })
    return time_str
}

// 表单重置
export function resetForm(refName) {
    if (this.$refs[refName]) {
        this.$refs[refName].resetFields();
    }
}

// 添加日期范围
export function addDateRange(params, dateRange, propName) {
    let search = params;
    search.params = typeof (search.params) === 'object' && search.params !== null && !Array.isArray(search.params) ? search.params : {};
    dateRange = Array.isArray(dateRange) ? dateRange : [];
    if (typeof (propName) === 'undefined') {
        search.params['beginTime'] = dateRange[0];
        search.params['endTime'] = dateRange[1];
    } else {
        search.params['begin' + propName] = dateRange[0];
        search.params['end' + propName] = dateRange[1];
    }
    return search;
}

// 添加检查日期范围
export function addStudyDateRange(params, dateRange) {
    let search = params;
    dateRange = Array.isArray(dateRange) ? dateRange : [];
    search.startDate = dateRange[0];
    search.endDate = dateRange[1];
    return search;
}

// 值转字符串
export function parseString(obj, ...keys) {
    keys.forEach(key => {
        if (obj[key] !== null) {
            obj[key] = obj[key] + '';
        }
    })
}

// 回显数据字典
export function selectDictLabel(datas, value) {
    if (value === undefined) {
        return "";
    }
    var actions = [];
    Object.keys(datas).some((key) => {
        if (datas[key].value == ('' + value)) {
            actions.push(datas[key].label);
            return true;
        }
    })
    if (actions.length === 0) {
        actions.push(value);
    }
    return actions.join('');
}

// 格式化年龄
export function formatAge(birthday, date) {
    // 计算年龄，1岁以内按月计算，1岁以上按岁计算，不足1个月按天计算
    if (birthday) {
        let age;
        const birth = new Date(birthday);
        const now = date ? new Date(date) : new Date();
        let year = now.getFullYear() - birth.getFullYear();
        let month = now.getMonth() - birth.getMonth();
        let day = now.getDate() - birth.getDate();
        if (month < 0 || (month === 0 && day < 0)) {
            year--;
            month += 12;
        }
        if (day < 0) {
            day += 30;
        }
        if (year > 0) {
            age = year + '岁';
        } else if (month > 0) {
            age = month + '个月';
        } else {
            age = day + '天';
        }
        return age;
    }
    return undefined;
}

// 回显数据字典（字符串数组）
export function selectDictLabels(datas, value, separator) {
    if (value === undefined || value.length === 0) {
        return "";
    }
    if (Array.isArray(value)) {
        value = value.join(",");
    }
    var actions = [];
    var currentSeparator = undefined === separator ? "," : separator;
    var temp = value.split(currentSeparator);
    Object.keys(value.split(currentSeparator)).some((val) => {
        var match = false;
        Object.keys(datas).some((key) => {
            if (datas[key].value == ('' + temp[val])) {
                actions.push(datas[key].label + currentSeparator);
                match = true;
            }
        })
        if (!match) {
            actions.push(temp[val] + currentSeparator);
        }
    })
    return actions.join('').substring(0, actions.join('').length - 1);
}

// 字符串格式化(%s )
export function sprintf(str) {
    var args = arguments, flag = true, i = 1;
    str = str.replace(/%s/g, function () {
        var arg = args[i++];
        if (typeof arg === 'undefined') {
            flag = false;
            return '';
        }
        return arg;
    });
    return flag ? str : '';
}

// 转换字符串，undefined,null等转化为""
export function parseStrEmpty(str) {
    if (!str || str == "undefined" || str == "null") {
        return "";
    }
    return str;
}

// 数据合并
export function mergeRecursive(source, target) {
    for (var p in target) {
        try {
            if (target[p].constructor == Object) {
                source[p] = mergeRecursive(source[p], target[p]);
            } else {
                source[p] = target[p];
            }
        } catch (e) {
            source[p] = target[p];
        }
    }
    return source;
};

/**
 * 构造树型结构数据
 * @param {*} data 数据源
 * @param {*} id id字段 默认 'id'
 * @param {*} parentId 父节点字段 默认 'parentId'
 * @param {*} children 孩子节点字段 默认 'children'
 */
export function handleTree(data, id, parentId, children) {
    let config = {
        id: id || 'id',
        parentId: parentId || 'parentId',
        childrenList: children || 'children'
    };

    var childrenListMap = {};
    var nodeIds = {};
    var tree = [];

    for (let d of data) {
        let parentId = d[config.parentId];
        if (childrenListMap[parentId] == null) {
            childrenListMap[parentId] = [];
        }
        nodeIds[d[config.id]] = d;
        childrenListMap[parentId].push(d);
    }

    for (let d of data) {
        let parentId = d[config.parentId];
        if (nodeIds[parentId] == null) {
            tree.push(d);
        }
    }

    for (let t of tree) {
        adaptToChildrenList(t);
    }

    function adaptToChildrenList(o) {
        if (childrenListMap[o[config.id]] !== null) {
            o[config.childrenList] = childrenListMap[o[config.id]];
        }
        if (o[config.childrenList]) {
            for (let c of o[config.childrenList]) {
                adaptToChildrenList(c);
            }
        }
    }

    return tree;
}

/**
 * 参数处理
 * @param {*} params  参数
 */
export function tansParams(params) {
    let result = ''
    for (const propName of Object.keys(params)) {
        const value = params[propName];
        var part = encodeURIComponent(propName) + "=";
        if (value !== null && value !== "" && typeof (value) !== "undefined") {
            if (typeof value === 'object') {
                for (const key of Object.keys(value)) {
                    if (value[key] !== null && value[key] !== "" && typeof (value[key]) !== 'undefined') {
                        let params = propName + '[' + key + ']';
                        var subPart = encodeURIComponent(params) + "=";
                        result += subPart + encodeURIComponent(value[key]) + "&";
                    }
                }
            } else {
                result += part + encodeURIComponent(value) + "&";
            }
        }
    }
    return result
}

// 格式化检查号输入
export function formatIntegerId(value) {
    const str = value.replace(/[^0-9]/g, '');
    if (str.length > 0) {
        const intVal = parseInt(str);
        if (intVal > 2147483647) {
            const temp = intVal.toString();
            return temp.substring(0, temp.length - 1)
        }
        return intVal;
    }
    return str;
}

// 返回项目路径
export function getNormalPath(p) {
    if (p.length === 0 || !p || p === 'undefined') {
        return p
    }
    let res = p.replace('//', '/')
    if (res[res.length - 1] === '/') {
        return res.slice(0, res.length - 1)
    }
    return res;
}

// 验证是否为blob格式
export function blobValidate(data) {
    return data.type !== 'application/json'
}

let timer = null;

export function throttle(fn, delay = 300) {
    if (timer) {
        clearTimeout(timer)
    }
    timer = setTimeout(() => {
        // 模拟触发change事件
        fn();
        // 清空计时器
        timer = null
    }, delay)
}

/**
 * 获得elem元素距相对定位的父元素的top
 * @param {HTMLElement} elem
 */
export function getElementTop(elem, direction) {
    let key = direction === 'top' ? 'offsetTop' : direction === 'left' ? 'offsetLeft' : 'offsetTop'
    var elemTop = elem[key];
    elem = elem.offsetParent;//将elem换成起相对定位的父元素
    while (elem != null) {//只要还有相对定位的父元素 
        //获得父元素 距他父元素的top值,累加到结果中
        elemTop += elem[key];
        //再次将elem换成他相对定位的父元素上;
        elem = elem.offsetParent;
    }
    return elemTop;
}

// 打开dicom页面
export function toDicom(eventId) {
    let url = window.location.origin + window.location.pathname + '#/dwv';
    url += `?id=${eventId}`
    // 处理在dicom页面又打开dicom的情况 这时候打开新的页面
    // "width=800,height=600,left=200,top=200,resizable=yes,scrollbars=yes,status=yes"
    if (window.parent.name === "cloud-dwv") {
        window.dwvWindow = window.open(url, "cloud-dwv-new");
    } else {
        window.dwvWindow = window.open(url, "cloud-dwv");
    }
    setTimeout(() => {
        localStorage.setItem('dwvOpen', 'open')
    }, 3000);
  }


// for循环 渲染赋值
export function handleCheckInfo(obj, listObj) {
    let copyListObj = JSON.parse(JSON.stringify(listObj))
    for (const key in copyListObj) {
        if (obj.hasOwnProperty(key)) {
            copyListObj[key].value = obj[key]
        } else {
            copyListObj[key].value = ''
        }
    }
    return copyListObj
}

export function resetCheckInfo(obj) {
    let copyListObj = JSON.parse(JSON.stringify(obj))
    for (const key in copyListObj) {
        if (copyListObj[key].hasOwnProperty('value')) {
            copyListObj[key].value = '';
        }
    }
    return copyListObj
}

// 处理报告模板数据
export function handleTreeData(data) {
    const arr = [];
    for (const key0 in data) {
        const modalityObj = {};
        modalityObj.label = key0; // 第一级名称是影像类型 如CT、US
        modalityObj.key = key0;
        modalityObj.children = [];
        for (const key1 in data[key0]) {
            const studypartObj = {};
            studypartObj.label = key1; // 第二级名称是科室 如产科、消化
            studypartObj.key = key1;
            studypartObj.children = [];
            modalityObj.children.push(studypartObj);
            for (const key2 in data[key0][key1]) {
                const negativePositiveObj = {};
                negativePositiveObj.key = key2;
                negativePositiveObj.label = key2; // 第三级名称是病总称
                negativePositiveObj.children = [];
                studypartObj.children.push(negativePositiveObj);
                for (const key3 in data[key0][key1][key2]) {
                    let v = data[key0][key1][key2][key3]
                    v.forEach(v => {
                        v.key = v.id;
                        v.label = v.diseaseDetails; // 第四级名称是病种
                        negativePositiveObj.children.push(v);
                    })
                }
            }
        }
        arr.push(modalityObj);
    }
    return arr;
}

export function getAssetsHomeFile(url) {
    const path = `../assets/images/${url}`;
    const modules = import.meta.glob("../assets/images/*", { eager: true });
    return modules[path]?.default;
}

export function getTimeAgo(time) {
    const currentTime = new Date();
    const targetTime = new Date(time);

    const timeDifference = currentTime.getTime() - targetTime.getTime();
    const seconds = Math.floor(timeDifference / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
        return `${days} 天前`;
    } else if (hours > 0) {
        return `${hours} 小时前`;
    } else if (minutes > 0) {
        return `${minutes} 分钟前`;
    } else {
        return `${seconds} 秒前`;
    }
}

// 身份证脱敏
export function desensitizeIdNumber(idNumber) {
    if (typeof idNumber !== 'string') {
        throw new Error('输入必须是字符串类型');
        // 或者使用其他逻辑处理非法输入
    }

    if (idNumber.length < 8) {
        throw new Error('输入的身份证号长度不足');
        // 或者使用其他逻辑处理不合规的输入
    }

    const len = idNumber.length;
    const startIndex = len <= 14 ? 3 : 6;
    const endIndex = len - 4;

    const sensitivePart = idNumber.substring(startIndex, endIndex);
    const maskedPart = sensitivePart.replace(/./g, '*');

    return idNumber.replace(sensitivePart, maskedPart);
}

// 出生日期 大于1年只显示年月日
export function formatBirthday(birthday) {
    // 计算年龄，1岁以内按月计算，1岁以上按岁计算，不足1个月按天计算
    if (birthday) {
        const date = new Date(birthday);
        const now = new Date();

        const diff = now - date;

        // 一年的毫秒数
        const oneYear = 365 * 24 * 60 * 60 * 1000;

        // if (diff < oneYear) {
        //     // 小于一年的情况，完整显示日期时间
        //     return parseTime(birthday)
        // } else {
            // 大于一年的情况，只显示日期
            return parseTime(birthday, '{y}-{m}-{d}');
        // }
    }
    return undefined;
}

export function isMobile() {
    if (window.navigator.userAgent.match(/(phone|pad|pod|iPhone|iPod|ios|iPad|Android|Mobile|BlackBerry|IEMobile|MQQBrowser|JUC|Fennec|wOSBrowser|BrowserNG|WebOS|Symbian|Windows Phone)/i)) {
        return true // 移动端
    } else {
        return false // PC端
    }
}

export const shortcuts = [
    {
        text: '今天',
        value: () => {
            return timeTools().dayRange(0, 0);
        },
    },
    {
        text: '昨天',
        value: () => {
            return timeTools().dayRange(-1, -1);
        },
    },
    {
        text: '前天',
        value: () => {
            return timeTools().dayRange(-2, -2);
        },
    },
    {
        text: '近七天',
        value: () => {
            return timeTools().dayRange(-6, 0);
        },
    },
    {
        text: '近一个月',
        value: () => {
            return timeTools().dayRange(-30, 0);
        },
    },
    // {
    // 	text: '七天前',
    // 	value: () => {
    // 		return ['2000-01-01 00:00:00', timeTools().dayRange(0,0)[1]];
    // 	},
    // },
];




