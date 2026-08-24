// This file exports TypeScript types and interfaces used throughout the application.

export interface User {
    id: number;
    name: string;
    email: string;
    createdAt: Date;
}

export interface Product {
    id: number;
    name: string;
    price: number;
    description?: string;
    createdAt: Date;
}

export interface Order {
    id: number;
    userId: number;
    productIds: number[];
    totalAmount: number;
    createdAt: Date;
}

export type ApiResponse<T> = {
    success: boolean;
    data?: T;
    error?: string;
};