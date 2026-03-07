interface PaginatedResponse<T> {
    count: number;
    results: T[];
}