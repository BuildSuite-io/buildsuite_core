export const SUB_COLS = [
  { key: 'code', label: 'ID' },
  { key: 'name', label: 'Name' },
  { key: 'status', label: 'Status' },
  { key: 'budget', label: 'Budget', align: 'right' },
  { key: 'progress', label: 'Progress', align: 'right' },
  { key: 'pm', label: 'PM' },
]

export const WP_COLS = [
  { key: 'code', label: 'Code' },
  { key: 'name', label: 'Name' },
  { key: 'status', label: 'Status' },
  { key: 'budget', label: 'Budget', align: 'right' },
  { key: 'progress', label: 'Progress', align: 'right' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'owner', label: 'Owner' },
]

export const TASK_COLS = [
  { key: 'name', label: 'Task' },
  { key: 'project', label: 'Project' },
  { key: 'status', label: 'Status' },
  { key: 'priority', label: 'Priority' },
  { key: 'task_type', label: 'Task Type' },
  { key: 'assignee', label: 'Assignee' },
  { key: 'endDate', label: 'Due' },
  { key: 'progress', label: 'Progress', align: 'right' },
]

export const BOQ_COLS = [
  { key: 'id', label: 'ID' },
  { key: 'title', label: 'Title' },
  { key: 'revision', label: 'Rev.', align: 'center' },
  { key: 'status', label: 'Status' },
  { key: 'sourceScoId', label: 'Source SCO' },
  { key: 'planned', label: 'Planned', align: 'right' },
  { key: 'actual', label: 'Actual', align: 'right' },
  { key: 'preparedDate', label: 'Prepared' },
]

export const SCO_COLS = [
  { key: 'id', label: 'ID' },
  { key: 'title', label: 'Title' },
  { key: 'impact', label: 'Impact', align: 'right' },
  { key: 'status', label: 'Status' },
  { key: 'raisedBy', label: 'Raised by' },
]

export const TEAM_COLS = [
  { key: 'member', label: 'Member' },
  { key: 'role', label: 'User' },
  { key: 'flag', label: '' },
]

export const PROJECT_REPORTS = [
  {
    slug: 'project-status-summary',
    icon: 'chart-line',
    label: 'Status summary',
    desc: 'Status, progress and schedule variance.',
  },
  {
    slug: 'stage-vs-actual',
    icon: 'calendar',
    label: 'Stage plan vs actual',
    desc: 'Planned vs completed task counts per stage.',
  },
  {
    slug: 'task-completion-by-week',
    icon: 'chart-line',
    label: 'Task completion by week',
    desc: 'Weekly completion burn for this project.',
  },
  {
    slug: 'pending-progress-entries',
    icon: 'file-text',
    label: 'Pending progress',
    desc: 'Tasks silent for 3+ days.',
  },
  {
    slug: 'labour-deployed',
    icon: 'workforce',
    label: 'Labour deployed',
    desc: 'Skilled + unskilled labour by task / week.',
  },
]
