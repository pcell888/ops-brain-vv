/**
 * CRM WebSocket 连接管理
 * 
 * 用于实时接收 CRM 线索事件（lead.created, lead.assigned, lead.converted, lead.lost）
 * 以及预警事件（response_timeout, follow_up_overdue 等）
 */

export type LeadEventType = 
  | 'lead.created' 
  | 'lead.assigned' 
  | 'lead.converted' 
  | 'lead.lost'
  | 'alert.triggered'
  | 'response_timeout'
  | 'follow_up_overdue'
  | 'roi_low'
  | 'budget_exhausted'
  | 'churn_risk_high'
  | 'task_overdue'
  | 'sync.completed'
  | 'rule.created'
  | 'workflow.created';

export type LeadStatus = 'created' | 'assigned' | 'contacted' | 'qualified' | 'negotiating' | 'converted' | 'lost' | 'other';

export interface Lead {
  id: string;
  crm_lead_id: string;
  lead_name: string;
  status: LeadStatus;
  lead_phone?: string;
  lead_email?: string;
  company_name?: string;
  source?: string;
  assigned_to?: string;
  assigned_at?: string;
  converted_at?: string;
  lost_at?: string;
  lost_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface LeadEvent {
  type: 'lead_event';
  event_type: LeadEventType;
  enterprise_id: string;
  lead: {
    id: string;
    crm_lead_id: string;
    lead_name: string;
    status: LeadStatus;
    created_at: string;
  };
}

export interface LeadStatusUpdate {
  type: 'lead_status_update';
  enterprise_id: string;
  lead_id: string;
  crm_lead_id: string;
  old_status: string;
  new_status: string;
  updated_fields: Record<string, unknown>;
}

export interface AlertEvent {
  type: 'alert';
  id: string;
  event_type: LeadEventType;
  crm_lead_id: string;
  lead_name?: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  created_at: string;
}

export interface ConnectedMessage {
  type: 'connected';
  message: string;
  channels: string[];
}

export interface HeartbeatMessage {
  type: 'heartbeat' | 'pong';
}

export type CRMWebSocketMessage = LeadEvent | LeadStatusUpdate | AlertEvent | ConnectedMessage | HeartbeatMessage;

type CRMMessageHandler = (message: CRMWebSocketMessage) => void;
type ConnectionHandler = (connected: boolean) => void;

class CRMWebSocketManager {
  private ws: WebSocket | null = null;
  private enterpriseId: string | null = null;
  private messageHandlers: Set<CRMMessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private pingInterval: NodeJS.Timeout | null = null;
  private isManualClose = false;

  /**
   * 连接到 CRM WebSocket
   */
  connect(enterpriseId: string) {
    if (this.ws && this.enterpriseId === enterpriseId && 
        this.ws.readyState === WebSocket.OPEN) {
      console.log('[CRM WebSocket] Already connected to', enterpriseId);
      return; // 已连接到相同的企业
    }

    // 如果正在连接中，不要重复连接
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      console.log('[CRM WebSocket] Connection in progress, skipping...');
      return;
    }

    this.disconnect(); // 先断开之前的连接
    this.enterpriseId = enterpriseId;
    this.isManualClose = false;

    // 动态构建 WebSocket URL
    let wsBaseUrl = import.meta.env.VITE_WS_URL;
    
    if (!wsBaseUrl && typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const hostname = window.location.hostname;
      const port = window.location.port;
      
      let finalPort = port;
      if (port === '13000') {
        finalPort = '18000';
      } else if (port === '3000' || !port) {
        finalPort = '8000';
      }
      
      wsBaseUrl = `${protocol}//${hostname}:${finalPort}`;
    }
    
    wsBaseUrl = wsBaseUrl || 'ws://localhost:8000';
    
    const wsUrl = `${wsBaseUrl}/api/v1/ws/crm/${enterpriseId}`;
    console.log('[CRM WebSocket] Connecting to:', wsUrl);
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('[CRM WebSocket] Connected to', enterpriseId);
        this.reconnectAttempts = 0;
        this.notifyConnectionHandlers(true);
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: CRMWebSocketMessage = JSON.parse(event.data);
          
          if (message.type === 'heartbeat') {
            this.send({ type: 'ping' });
          } else {
            this.notifyMessageHandlers(message);
          }
        } catch (e) {
          console.error('[CRM WebSocket] Failed to parse message:', e);
        }
      };

      this.ws.onclose = (event) => {
        console.log('[CRM WebSocket] Disconnected:', event.code, event.reason);
        this.stopPing();
        this.notifyConnectionHandlers(false);
        
        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('[CRM WebSocket] Error:', error);
      };
    } catch (e) {
      console.error('[CRM WebSocket] Failed to create connection:', e);
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isManualClose = true;
    this.stopPing();
    
    if (this.ws) {
      // 延迟关闭，避免 React Strict Mode 双重渲染导致的连接中断
      setTimeout(() => {
        if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
          this.ws.close();
          this.ws = null;
        }
      }, 500);
    }
    
    this.enterpriseId = null;
    this.reconnectAttempts = 0;
  }

  /**
   * 发送消息
   */
  private send(data: object) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  /**
   * 启动心跳
   */
  private startPing() {
    this.stopPing();
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 25000);
  }

  /**
   * 停止心跳
   */
  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * 计划重连
   */
  private scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[CRM WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      if (this.enterpriseId && !this.isManualClose) {
        this.connect(this.enterpriseId);
      }
    }, delay);
  }

  /**
   * 注册消息处理器
   */
  onMessage(handler: CRMMessageHandler) {
    this.messageHandlers.add(handler);
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  /**
   * 注册连接状态处理器
   */
  onConnectionChange(handler: ConnectionHandler) {
    this.connectionHandlers.add(handler);
    return () => {
      this.connectionHandlers.delete(handler);
    };
  }

  /**
   * 通知所有消息处理器
   */
  private notifyMessageHandlers(message: CRMWebSocketMessage) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (e) {
        console.error('[CRM WebSocket] Handler error:', e);
      }
    });
  }

  /**
   * 通知所有连接状态处理器
   */
  private notifyConnectionHandlers(connected: boolean) {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected);
      } catch (e) {
        console.error('[CRM WebSocket] Connection handler error:', e);
      }
    });
  }

  /**
   * 获取连接状态
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// 导出单例
export const crmWsManager = new CRMWebSocketManager();
