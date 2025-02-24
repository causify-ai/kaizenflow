pragma solidity ^0.8.0;

library OrderMinHeap {
    struct Order {
        uint256 index;
        address walletAddress;
        address baseToken;
        address quoteToken;
        uint256 quantity;
        uint256 limitPrice;
        bool isBuy;
        address depositAddress;
        uint256 timestamp;
    }

    struct Heap {
        uint32 size;
        Order[] data;
    }

    /// @notice Initializes the heap with a size of 0
    /// @param self The heap structure to initialize
    function createHeap(Heap storage self) internal {
        self.size = 0;
    }

    /// @notice Inserts an order into the heap while maintaining the min-heap property
    /// @param self The heap structure to insert the order into
    /// @param order The order to be inserted
    function insert(Heap storage self, Order storage order) internal {
        if (self.size == self.data.length) {
            self.data.push();
        }
        uint32 _index = self.size++;
        while (
            _index > 0 && self.data[parent(_index)].quantity > order.quantity
        ) {
            self.data[_index] = self.data[parent(_index)];
            _index = parent(_index);
        }
        self.data[_index] = order;
    }

    /// @notice Removes the top (smallest) element from the heap
    /// @param self The heap structure to remove the top element from
    function removeTop(Heap storage self) internal {
        require(self.size > 0, "Heap underflow");
        self.data[0] = self.data[--self.size];
        heapify(self, 0);
    }

    /// @notice Returns the index of the top element in the heap
    function topIndex(Heap storage self) internal view returns (uint256) {
        require(self.size > 0, "Heap underflow");
        return self.data[0].index;
    }

    /// @notice Calculates the parent index for a given index
    function parent(uint32 i) private pure returns (uint32) {
        return (i - 1) / 2;
    }

    /// @notice Calculates the left child index for a given index
    function left(uint32 i) private pure returns (uint32) {
        return 2 * i + 1;
    }

    /// @notice Calculates the left child index for a given index
    function right(uint32 i) private pure returns (uint32) {
        return 2 * i + 2;
    }

    /**
     * @notice Reorganizes the heap to maintain the min-heap property after removing the top element.
     * @dev This function is called after removing the top element from the heap to ensure that the
     * heap remains a valid min-heap. It starts at the given index and compares the element with
     * its children. If the element is greater than any of its children, it swaps the element
     * with the smallest child and continues the process down the heap until the min-heap
     * property is satisfied.
     *
     * @param self The heap structure to reorganize
     * @param i The index at which to start reorganizing the heap
     */
    function heapify(Heap storage self, uint32 i) private {
        while (true) {
            uint32 min = i;
            uint32 leftChild = left(i);
            uint32 rightChild = right(i);

            if (
                leftChild < self.data.length &&
                self.data[leftChild].quantity < self.data[min].quantity
            ) {
                min = leftChild;
            }
            if (
                rightChild < self.data.length &&
                self.data[rightChild].quantity < self.data[min].quantity
            ) {
                min = rightChild;
            }

            if (min != i) {
                (self.data[i], self.data[min]) = (self.data[min], self.data[i]);
                i = min;
            } else {
                break;
            }
        }
    }
}
