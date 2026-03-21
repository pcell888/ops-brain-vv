/**
 * WebSocket 连接管理
 */

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface TaskStatusMessage {
  type: 'task_status';
  task_type: 'diagnosis' | 'solution' | 'tracking';
  task_id: string;
  enterprise_id: string;
  status: TaskStatus;
  progress: number;
  message: string | null;
  data: Record<string, unknown> | null;
}

export interface HeartbeatMessage {
  type: 'heartbeat' | 'pong';
}

export interface ConnectedMessage {
  type: 'connected';
  message: string;
}

export type WebSocketMessage = TaskStatusMessage | HeartbeatMessage | ConnectedMessage;

type MessageHandler = (message: TaskStatusMessage) => void;
type ConnectionHandler = (connected: boolean) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private enterpriseId: string | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private pingInterval: NodeJS.Timeout | null = null;
  private isManualClose = false;

  /**
   * 连接到 WebSocket
   */
  connect(enterpriseId: string) {
    if (this.ws && this.enterpriseId === enterpriseId && 
        this.ws.readyState === WebSocket.OPEN) {
      return; // 已连接到相同的企业
    }

    this.disconnect(); // 先断开之前的连接
    this.enterpriseId = enterpriseId;
    this.isManualClose = false;

    // 与页面同源（经 Vite / nginx 的 /api 反代），避免直连后端端口导致连不上、进度一直为 0
    const wsBase =
      import.meta.env.VITE_WS_URL ||
      (typeof window !== 'undefined'
        ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
        : 'ws://localhost:8000');
    const wsUrl = `${wsBase.replace(/\/$/, '')}/api/v1/ws/tasks/${enterpriseId}`;
    console.log('[WebSocket] Connecting to:', wsUrl);
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to', enterpriseId);
        this.reconnectAttempts = 0;
        this.notifyConnectionHandlers(true);
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          if (message.type === 'task_status') {
            this.notifyMessageHandlers(message);
          } else if (message.type === 'heartbeat') {
            // 收到服务器心跳，发送 pong
            this.send({ type: 'ping' });
          }
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e);
        }
      };

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        this.stopPing();
        this.notifyConnectionHandlers(false);
        
        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };
    } catch (e) {
      console.error('[WebSocket] Failed to create connection:', e);
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isManualClose = true;
    this.stopPing();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
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
    }, 25000); // 每25秒发送一次ping
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
    
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      if (this.enterpriseId && !this.isManualClose) {
        this.connect(this.enterpriseId);
      }
    }, delay);
  }

  /**
   * 注册消息处理器
   */
  onMessage(handler: MessageHandler) {
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
  private notifyMessageHandlers(message: TaskStatusMessage) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (e) {
        console.error('[WebSocket] Handler error:', e);
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
        console.error('[WebSocket] Connection handler error:', e);
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
export const wsManager = new WebSocketManager();

