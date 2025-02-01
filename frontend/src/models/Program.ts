export interface Program {
  id: string;
  title: string;
  start: Date;
  end: Date;
  duration: number;
  description?: string;
  category?: string;
} 