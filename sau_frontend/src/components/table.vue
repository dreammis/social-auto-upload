<template>
  <div class="table-container">
    <div class="tableToolbar">
      <el-tooltip class="item" effect="dark" content="显隐列" placement="top">
        <el-dropdown trigger="click" :hide-on-click="false" style="padding-left: 12px;opacity: 0.7;" :key="dropdownKey" max-height="400">
          <el-button circle icon="Menu" />
          <template #dropdown>
            <el-dropdown-menu>
              <template v-for="item in allCopyColumn" :key="item.key">
                <el-dropdown-item>
                  <el-checkbox :checked="!item.hidden" @change="checkboxChange($event, item.title)" :label="item.title" />
                </el-dropdown-item>
              </template>
              <!-- 添加重置按钮 -->
              <el-dropdown-item>
                <el-button 
                  type="text" 
                  style="width: 100%; text-align: center"
                  @click="resetColumnConfig"
                >
                  重置列设置
                </el-button>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-tooltip>
    </div>
    <div class="YsModule-table" ref="YsModuleTable">
      <el-table
        ref="tableRef"
        class="generalListClassName"
        :span-method="cellMerge"
        stripe
        :data="props.data"
        highlight-current-row
        :border="true"
        @selection-change="handleSection"
        :row-class-name="rowClassName"
        current-row-key="index"
        :align="'center'"
        style="width: 100%"
        :height="tableHeight"
        :size="props.size"
        scrollbar-always-on
        @row-dblclick="dblclick"
        @row-click="click"
        @row-contextmenu="contextmenu"
        @header-dragend="handelWidth"
        @sort-change="sortChange"
      >
        <el-table-column
          v-if="props.showOperation"
          :align="'center'"
          type="selection"
          width="55"
          :selectable="selectable"
        ></el-table-column>
        <el-table-column
          label="序号"
          v-if="props.showIndex"
          align="center"
          type="index"
          width="55"
        ></el-table-column>
        <el-table-column
          v-for="column in copyColumn"
          :prop="column.key"
          :label="column.title"
          :align="column.align ? column.align : 'center'"
          :width="column.width"
          :min-width="column.minWidth"
          :key="column.key"
          :type="column.type"
          :show-overflow-tooltip="column.tag || column.key === 'operation' || column.hideOverflowTooltip ? false :true"
          :fixed="column.fixed || undefined"
          :sortable="column.hasOwnProperty('sortable') ? column.sortable : ['operation'].includes(column.key) ? false : true"
        >
          <template #default="scope">
            <slot
              v-if="column.slots"
              :name="column.slots"
              :data="scope.row"
            ></slot>

            <dict-tag
              v-else-if="column.tag"
              :options="column.options"
              :tagWidth="column.tagWidth"
              :value="checkKey(column, scope)"
            />

            <el-link
                v-else-if="column.link"
                :underline="false"
                @click="column.click && column.click(scope.row)"
                :type="column.type || 'primary'">
              {{ checkKey(column, scope) }}
            </el-link>

            <el-image
              v-else-if="column.img"
              style="width: 80px"
              :src="checkKey(column, scope)"
              :preview-src-list="[checkKey(column, scope)]"
              class="mt10"
              :preview-teleported="true"
              hide-on-click-modal
            >
              <template #error>
                <img
                  src="https://img.dengyuan.vip/static/logo-fang.ico"
                  style="width: 80px"
                  alt=""
                />
              </template>
            </el-image>
            <div v-else>{{ checkKey(column, scope) }}</div>
          </template>
        </el-table-column>
      </el-table>
      <!--分页栏-->
      <div class="toolbar" v-if="!props.nonePagination">
        <div class="pagination">
          <el-pagination
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
            :current-page="props.modelValue.pageNum"
            :page-sizes="[10, 20, 30, 50]"
            :page-size="props.modelValue.pageSize"
            background
            layout="total, sizes, pager, prev, next,jumper"
            :total="props.total"
          >
          </el-pagination>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup name="Table">
import { ref, nextTick, onMounted, onBeforeUnmount, onActivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getElementTop } from "@/utils/pacs";
import cache from '@/plugins/cache';
import Sortable from 'sortablejs';
import { ElMessage  } from 'element-plus'
import DictTag from './DictTag.vue'

const props = defineProps({
  modelValue: {
    default: Object,
  },
  // 表格列配置
  columns: {
    type: [Object,Array],
    default: [],
  },
  // 表格数据
  data: {
    type: Array,
    default: [],
  },
  total: {
    //表格总页数
    type: Number,
    default: null,
  },
  height: {
    // 表格最大高度
    type: String,
    default: '100%',
  },
  columnCell: {
    type: Array,
    default: null,
  },
  size: {
    type: String,
    default: "default",
  },
  // 是否显示勾选
  showOperation: {
    type: Boolean,
    default: false,
  },
  // 是否显示index
  showIndex: {
    type: Boolean,
    default: false,
  },
  // 不需要分页
  nonePagination: {
    type: Boolean,
    default: false,
  },
  selectableConfig: {
    type: Object,
    default: {
      self: false,
      selfFunc: () => {},
    },
  },
  hiddenColumnOptions: {
    type: Array,
    default: () => [],
  }
});

const emit = defineEmits([
  "clear",
  "handleSection",
  "dbClick",
  "rowClick",
  "rowContextmenu",
  "clearSelection",
  "sortChange",
  "setCurrentRow"
]);

const route = useRoute();
const cellIndex = ref(0)
const tableHeight = ref(0)
const tableRef = ref()
const YsModuleTable = ref()
const allCopyColumn = ref([])
const copyColumn = ref([])
const dropdownKey = ref(0);
const widthLocalKey = `localWidth_${route.path}`
const scrollKey = `table_scroll_${route.path}`
const headerKey = `table_header_${route.path}`

let sortable = null;
const CHAR_WIDTH = parseInt((parseInt(sessionStorage.getItem('size') || '15') / 15) * 16);
const SORT_ICON_WIDTH = parseInt((parseInt(sessionStorage.getItem('size') || '15') / 15) * 26.5);
const PADDING_WIDTH = parseInt((parseInt(sessionStorage.getItem('size') || '15') / 15) * 6 * 2);

onMounted(() => {
  nextTick(() => {
    calcTableHeight();
    initTableHeaderDrag()

    // 表格高度记忆
    const scrollEl = getScrollEl()
    scrollEl?.addEventListener('scroll', handleScroll)
  })
});

onBeforeUnmount(() => {
  const scrollEl = getScrollEl()
  scrollEl?.removeEventListener('scroll', handleScroll)
})

onActivated(() => {
  restoreScroll()
})

// 计算表格高度
const calcTableHeight = () => {
  let parent = YsModuleTable.value
  let paginationHeight = 0;
  if (!props.nonePagination) {
    paginationHeight = parent.querySelector('.pagination').offsetHeight
  }
  if (props.height) {
    if (props.height === '100%') {
      tableHeight.value = `calc(100% - ${paginationHeight}px)`
    } else {
      tableHeight.value = props.height;
    }
    return;
  }
  let table = tableRef.value;
  if (!table) return;
  let tableOffsetTop = getElementTop(table);

  let height;

  height =
    document.body.offsetHeight -
    paginationHeight -
    tableOffsetTop;
  tableHeight.value = height;
};

const cellMerge = ({ row, columnIndex }) => {
  if (
    props.columnCell != undefined &&
    props.columnCell.indexOf(columnIndex) !== -1
  ) {
    return {
      rowspan: row._length,
      colspan: 1,
    };
  }
};
// 获取勾选的表格id
const handleSection = (val) => {
  let tableChecked = val.map((s) => s);
  emit("handleSection", tableChecked);
};
const selectable = (row, rowIndex) => {
  if (props.selectableConfig.self) {
    return props.selectableConfig.selfFunc(row, rowIndex);
  } else {
    return true; // 默认全部可选
  }
};
// 给相应的rowIndex添加类名
const rowClassName = (row, rowIndex) => {
  let r = -1;
  props.data.forEach(() => {
    if (cellIndex.value === row.orderNo) {
      r = rowIndex;
    }
  });
  if (rowIndex === r) {
    return "hover-row";
  }
};
// 分页
const handleSizeChange = (pageSize) => {
  // eslint-disable-next-line vue/no-mutating-props
  props.modelValue.pageNum = 1;
  // eslint-disable-next-line vue/no-mutating-props
  props.modelValue.pageSize = pageSize;
  emit("clear", props.modelValue);
};
const handleCurrentChange = (pageNum) => {
  // eslint-disable-next-line vue/no-mutating-props
  props.modelValue.pageNum = pageNum;
  emit("clear", props.modelValue);
};
// 检查显示字段
const checkKey = (column, scope) => {
  if (scope.row[column.key] === undefined) return '-'
  return column.key.includes(".")
    ? scope.row[column.key.split(".")[0]] &&
        scope.row[column.key.split(".")[0]][column.key.split(".")[1]]
    : scope.row[column.key] || scope.row[column.key] === 0
    ? scope.row[column.key]
    : "-";
};
// 双击
const dblclick = (row, column, event) => {
  emit("dbClick", { row, column, event });
};

// 左键点击
const click = (row, column, event) => {
  emit("rowClick", { row, column, event });
};

// 右键点击
const contextmenu = (row, column, event) => {
  emit("rowContextmenu", { row, column, event });
};

const handelWidth = (newWidth, oldWidth, column) => {
  if (widthLocalKey) {
    setLocal(column);
  }
}

const getLocal = () => {
  if (!widthLocalKey) return;
  let local = cache.local.getJSON(widthLocalKey);
  return local
};

const setLocal = (column) => {
  if (!widthLocalKey) return;
  let key
  const { label, property, width } = column;
  if (label === '序号') return
  // 每个页面的操作栏独立保存
  // if (property === 'operation') {
  //   key = route.name + property
  // } else {
    key = property
  // }

  let local = getLocal();
  if (!local) {
    local = [];
  }
  const index = local.findIndex((v) => v.prop === key);
  if (index !== -1) {
    local[index].width = width;
  } else {
    local.push({
      prop: key,
      width
    })
  }
  cache.local.setJSON(widthLocalKey, local)
};

const handleColumn = (e) => {
  const columns = JSON.parse(JSON.stringify(e));
  
  allCopyColumn.value = columns.map(column => ({
    ...column,
    hidden: column.hidden || false,
    minWidth: calculateMinWidth(column),
    width: column.flex ? null : Math.max(column.width, calculateMinWidth(column))
  })); 

  copyColumn.value = allCopyColumn.value.filter(column => !column.hidden);
  
  // 处理本地存储的宽度
  let local = getLocal();
  if (local) {
    copyColumn.value = copyColumn.value.map(v => {
      if (v.flex) {
        v.width = null
        return v
      };
      
      let item = local.find((b) => b.prop === v.key);
      
      return item ? { ...v, width: Math.max(item.width, v.minWidth) } : v;
    });
  }
};

const initTableHeaderDrag = () => {
  if(sortable) sortable.destroy()
  if (!YsModuleTable.value) return
  const el = YsModuleTable.value.querySelector('.el-table__header-wrapper tr')
  sortable = Sortable.create(el, {
    animation: 150,
    ghostClass: 'blue-background-class',
    filter: '.el-table__header-wrapper tr th.el-table-fixed-column--left, .el-table__header-wrapper tr th.el-table-fixed-column--right',
    onEnd: function (e) {
      let { oldIndex, newIndex } = e
      // 调整索引以排除固定列的影响
      const fixedColumnsCount = props.showOperation + props.showIndex;
      if (oldIndex < fixedColumnsCount || newIndex < fixedColumnsCount) return;
      oldIndex -= fixedColumnsCount;
      newIndex -= fixedColumnsCount;
      if (oldIndex < 0 || newIndex < 0 || oldIndex >= copyColumn.value.length || newIndex >= copyColumn.value.length) return;
      
      let oldItem = copyColumn.value[oldIndex]
      let newItem = copyColumn.value[newIndex]
      copyColumn.value.splice(oldIndex, 1)
      copyColumn.value.splice(newIndex, 0, oldItem)

      let oldI = allCopyColumn.value.findIndex(v => v.key === oldItem.key)
      let newI = allCopyColumn.value.findIndex(v => v.key === newItem.key)
      let old = allCopyColumn.value[oldI]
      allCopyColumn.value.splice(oldI, 1)
      allCopyColumn.value.splice(newI, 0, old)
      cache.session.setJSON(headerKey, allCopyColumn.value)
    }
  })
}

//清除选中的值
const clearSelection = () => {
  tableRef.value?.clearSelection();
};

const sortChange = ({ column, prop, order }) => {
  order = order === 'ascending' ? 'ASC' : order === 'descending' ? 'DESC' : ''
  emit('sortChange', { prop, order })
}

const setCurrentRow = (row) => {
  tableRef.value?.setCurrentRow(row);
}

const getScrollEl = () => {
  return tableRef.value?.$el?.querySelector('.el-table__body-wrapper .el-scrollbar__wrap')
}

const handleScroll = (e) => {
  const { scrollTop, scrollLeft } = e.target
  window[scrollKey] = { scrollTop, scrollLeft }
}

const restoreScroll = () => {
  nextTick(() => {
    if (tableRef.value) {
      const scrollEl = getScrollEl()
      const savedScroll = window[scrollKey]
      if (savedScroll) {
        const { scrollTop, scrollLeft } = savedScroll
        scrollEl.scrollTop = scrollTop
        scrollEl.scrollLeft = scrollLeft
      }
    }
  })
}

// 选择显示列
const checkboxChange = (e, title) => {
  allCopyColumn.value.filter(item => item.title == title)[0].hidden = !e
  copyColumn.value = allCopyColumn.value.filter(column => column.hidden === false)
  cache.session.setJSON(headerKey, allCopyColumn.value)
}

const resetColumnConfig = () => {
  // 清除本地存储的列配置
  cache.session.remove(headerKey)
  cache.local.remove(widthLocalKey)
  // 重置为props.columns的默认配置
  const defaultColumns = JSON.parse(JSON.stringify(props.columns));
  // 完全重置所有列状态
  if(props.hiddenColumnOptions && props.hiddenColumnOptions.length > 0) {
    allCopyColumn.value = props.hiddenColumnOptions
  } else {
  allCopyColumn.value = defaultColumns.map(column => ({
    ...column,
    hidden: false, // 重置所有列为显示状态
    minWidth: calculateMinWidth(column) // 重新计算最小宽度
  }));
  }

  copyColumn.value = [...allCopyColumn.value]; // 复制一份作为显示的列

  // 强制重新渲染下拉菜单
  dropdownKey.value++;

  ElMessage.success('列配置已重置为默认设置')
}

// 提取最小宽度计算逻辑
const calculateMinWidth = (column) => {
  let minWidth = 0;
  if (column.title) {
    minWidth += column.title.length * CHAR_WIDTH;
  }

  const isSortable = column.hasOwnProperty('sortable') 
    ? column.sortable 
    : ['operation'].includes(column.key) 
      ? false 
      : true;

  if (isSortable) {
    minWidth += SORT_ICON_WIDTH;
  }

  minWidth += PADDING_WIDTH; // 左右padding
  
  return column.minWidth || minWidth;
};

const sortMethod = (a, b, key, order = 'ASC') => {
  const valueA = a[key];
  const valueB = b[key];

  if (key.includes('age') || key.includes('Age')) {
    const parseAgeToDays = (ageStr) => {
      if (!ageStr) return 0;

      let years = 0, months = 0, days = 0;

      const yearMatch = ageStr.match(/(\d+)(?:岁|年)/g);
      
      const monthMatch = ageStr.match(/(\d+)(?:个月|月)/gi);
      const dayMatch = ageStr.match(/(\d+)(?:天|日)/gi);
      if (yearMatch) {
        yearMatch.forEach(m => {
          const num = m.match(/\d+/);
          if (num) years += parseInt(num[0]);
        });
      }

      if (monthMatch) {
        monthMatch.forEach(m => {
          const num = m.match(/\d+/);
          if (num) months += parseInt(num[0]);
        });
      }

      if (dayMatch) {
        dayMatch.forEach(m => {
          const num = m.match(/\d+/);
          if (num) days += parseInt(num[0]);
        });
      }

      return years * 365 + months * 30 + days;
    };

    const valA = parseAgeToDays(valueA);
    const valB = parseAgeToDays(valueB);

    return valA - valB;
  }

  // 空值处理
  if(!valueA || !valueB) {
    if (!valueA && valueB) return -1;
    if (valueA && !valueB) return 1;
    if (valueA && valueB) return 0;
  }

  // 处理数字
  if (typeof valueA === 'number' && typeof valueB === 'number') {
    return order === 'ASC' ? valueA - valueB : valueB - valueA;
  }

  // 数字开头的排最前，字母第二，其他按中文排序
  const getTypePriority = (str) => {
    if (/^\d/.test(str)) return 1;     // 数字开头
    if (/^[A-Za-z]/.test(str)) return 2; // 字母开头
    return 3;                          // 其他（中文等）
  };

  const priorityA = getTypePriority(valueA);
  const priorityB = getTypePriority(valueB);

  if (priorityA !== priorityB) {
    return priorityA - priorityB;
  }

  // 处理字符串（包括中文、字母）
  if (typeof valueA === 'string' && typeof valueB === 'string') {
    return order === 'ASC'
      ? valueA.localeCompare(valueB, 'zh')
      : valueB.localeCompare(valueA, 'zh');
  }

  // 处理日期（ISO格式或时间戳）
  const dateA = new Date(valueA);
  const dateB = new Date(valueB);
  if (!isNaN(dateA) && !isNaN(dateB)) {
    return order === 'ASC' ? dateA - dateB : dateB - dateA;
  }

  // 默认回退
  return 0;
};

watch(
  () => props.hiddenColumnOptions,
  (newVal) => {
    allCopyColumn.value = newVal
  },
  {
    immediate: true,
    deep: true // 添加深度监听
  }
)

watch(
  () => props.columns,
  (newVal) => {
    // 确保新值有效且非空
    if (!newVal || newVal.length === 0) return
    
    // 优先使用props.columns，仅在缓存存在且用户未修改列显示时使用缓存
    const cached = cache.session.getJSON(headerKey)
    const finalColumns = cached && cached.length === newVal.length 
      ? cached 
      : newVal
    
    handleColumn(finalColumns)
  },
  {
    immediate: true,
    deep: true // 添加深度监听
  }
)

watch(
  () => props.data, // 监听表格数据
  (newData, oldData) => {
    if (newData !== oldData && oldData.length !== 0) {
      const savedScroll = window[scrollKey]
      const scrollLeft = savedScroll?.scrollLeft || 0
      window[scrollKey] = { scrollTop: 0, scrollLeft }
      restoreScroll() // 数据变化时滚动到顶部
    }
  },
  { deep: true } // 深度监听（如果数据是对象/数组）
)

defineExpose({
  setCurrentRow
});
</script>

<style>
/* 置灰也要勾选显示 */
.special-general-list  .el-checkbox__input.is-disabled::before{
  content: "";
  box-sizing: content-box;
  display: block;
  border: 1px solid #bebebe;
  border-left: 0;
  border-top: 0;
  height: 7px;
  left: 5px;
  position: absolute;
  top: 2px;
  z-index: 9;
  transform: rotate(45deg) scaleY(0);
  width: 3px;
  transform-origin: center;
  transform: rotate(45deg) scaleY(1);
}
</style>
<style lang="scss" scoped>
.table-container {
  height: 100%;
  position: relative;
}
.tableToolbar {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 111;
}
.YsModule-table {
  height: 100%;
  :deep(.el-table__inner-wrapper) {
    height: 100% !important;
  }
}
:deep(.el-table .cell) {
  padding: 0 5px;
}
:deep(.el-table .cell.el-tooltip > div) {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
:deep(.el-table .el-link) {
  width: 100%;
}
:deep(.el-table .el-link__inner) {
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
:deep(.el-scrollbar__thumb) {
  position: absolute !important;
}
.pagination {
  padding-top: 7px;
  display: flex;
  justify-content: center;
}
</style>
