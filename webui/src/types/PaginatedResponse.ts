// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

interface PaginatedResponse<T> {
    count: number;
    results: T[];
}

export default PaginatedResponse
