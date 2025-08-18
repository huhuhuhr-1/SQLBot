import mysql_ds from '@/assets/datasource/icon_mysql.png'
import excel from '@/assets/datasource/icon_excel.png'
import oracle from '@/assets/datasource/icon_oracle.png'
import pg from '@/assets/datasource/icon_PostgreSQL.png'
import sqlServer from '@/assets/datasource/icon_SQL_Server.png'
import ck from '@/assets/datasource/icon_ck.png'
import { i18n } from '@/i18n'

const t = i18n.global.t
export const dsType = [
  { label: t('ds.local_excelcsv'), value: 'excel' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'Oracle', value: 'oracle' },
  { label: 'PostgreSQL', value: 'pg' },
  { label: 'SQL Server', value: 'sqlServer' },
  { label: 'ClickHouse', value: 'ck' },
]

export const dsTypeWithImg = [
  { name: t('ds.local_excelcsv'), type: 'excel', img: excel },
  { name: 'MySQL', type: 'mysql', img: mysql_ds },
  { name: 'Oracle', type: 'oracle', img: oracle },
  { name: 'PostgreSQL', type: 'pg', img: pg },
  { name: 'SQL Server', type: 'sqlServer', img: sqlServer },
  { name: 'ClickHouse', type: 'ck', img: ck },
]

export const haveSchema = ['sqlServer', 'pg', 'oracle']
