interface PaginatedResponse<T> {
    count: number;
    results: T[];
}

export default PaginatedResponse
