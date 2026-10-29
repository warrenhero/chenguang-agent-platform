export interface User {
  id: string
  username: string
  email: string
  name: string
  avatar?: string
  role: string
  status: 'active' | 'inactive' | 'disabled'
  department?: string
  lastLoginAt?: string
  createdAt: string
}

export interface Role {
  id: string
  name: string        // 角色编码，如 admin
  displayName: string // 角色显示名，如 系统管理员
  description: string
  permissions: string[]
  userCount: number
  createdAt: string
  updatedAt: string
}

export interface ApiKey {
  id: string
  name: string
  key: string
  permissions: string[]
  status: 'active' | 'disabled' | 'expired'
  rateLimit: number
  usageCount: number
  lastUsedAt?: string
  expiresAt?: string
  createdBy: string
  createdAt: string
}

export interface AuditLog {
  id: string
  userId: string
  userName: string
  action: string
  resource: string
  resourceName: string
  details: Record<string, unknown>
  ip: string
  userAgent: string
  status: 'success' | 'failed'
  timestamp: string
}

export interface AlertRule {
  id: string
  name: string
  description: string
  condition: {
    metric: string
    operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte'
    threshold: number
    duration: number
  }
  status: 'enabled' | 'disabled'
  createdBy: string
  createdAt: string
  updatedAt: string
}

export interface ActiveAlert {
  id: string
  ruleId: string
  ruleName: string
  level: 'info' | 'warning' | 'error' | 'critical'
  message: string
  triggeredAt: string
  duration: string
  status: 'active' | 'acknowledged' | 'resolved'
}

export interface SystemAlert {
  id: string
  type: 'error' | 'warning' | 'info'
  title: string
  message: string
  source: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: 'active' | 'acknowledged' | 'resolved'
  count: number
  firstOccurredAt: string
  lastOccurredAt: string
  acknowledgedBy: string | null
  acknowledgedAt?: string
  resolvedAt?: string
}

export interface SystemSettingsBasic {
  siteName: string
  description: string
  siteUrl: string
  logo: string
  favicon: string
  timezone: string
  language: string
}

export interface SystemSettingsSecurity {
  passwordMinLength: number
  passwordRequireUppercase: boolean
  passwordRequireNumber: boolean
  passwordRequireSpecial: boolean
  sessionTimeout: number
  maxLoginAttempts: number
  lockoutDuration: number
  enableTwoFactor: boolean
}

export interface SystemSettingsNotification {
  enableEmail: boolean
  emailProvider: string
  smtpHost: string
  smtpPort: number
  smtpUser: string
  smtpFrom: string
  enableWebhook: boolean
  webhookUrl: string
}

export interface SystemSettingsStorage {
  provider: string
  region: string
  bucket: string
  maxFileSize: number
  allowedFileTypes: string[]
}

export interface SystemSettingsModel {
  defaultProvider: string
  defaultModel: string
  maxTokens: number
  temperature: number
  timeout: number
}

export interface SystemSettingsRateLimit {
  enableRateLimit: boolean
  defaultLimit: number
  windowSize: number
  enableIpWhitelist: boolean
  ipWhitelist: string[]
}

export interface SystemSettings {
  basic: SystemSettingsBasic
  security: SystemSettingsSecurity
  notification: SystemSettingsNotification
  storage: SystemSettingsStorage
  model: SystemSettingsModel
  rateLimit: SystemSettingsRateLimit
}
