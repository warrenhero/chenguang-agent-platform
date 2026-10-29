import { mockDashboardService } from './mock/dashboard';

// 后端尚未实现该模块接口，固定使用 Mock；后端就绪后恢复 USE_MOCK 三元切换
export const dashboardService = mockDashboardService;
