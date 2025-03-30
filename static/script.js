function fetchInventory() {
    fetch("/get_inventory")
    .then(response => response.json())
    .then(data => {
        let tbody = document.querySelector("#inventoryTable tbody");
        tbody.innerHTML = "";

        data.forEach(item => {
            let row = `<tr>
                <td>${item.item_code}</td>
                <td>${item.item_name}</td>
                <td>${item.item_quantity}</td>
                <td>${item.cost_per_item}</td>
                <td>${item.profit_percentage}</td>
                <td>
                    <button class="btn btn-primary" onclick="openEditModal('${item.item_code}', '${item.item_name}', ${item.item_quantity}, ${item.cost_per_item}, ${item.profit_percentage})">Edit</button>
                    <button class="btn btn-danger" onclick="confirmDelete('${item.item_code}', '${item.item_name}')">Delete</button>
                </td>
            </tr>`;
            tbody.innerHTML += row;
        });
    })
    .catch(error => console.error("Error fetching inventory:", error));
}



function addItem() {
    let itemCode = document.getElementById("addCode").value;
    let itemName = document.getElementById("addName").value;
    let itemQuantity = document.getElementById("addQuantity").value;
    let itemCost = document.getElementById("addCost").value;
    let itemProfit = document.getElementById("addProfit").value;

    fetch("/add_item", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            code: itemCode,
            name: itemName,
            quantity: parseInt(itemQuantity),
            cost: parseFloat(itemCost),
            profit: parseFloat(itemProfit),
        }),
    })
    .then(response => response.json())
    .then(() => {
        fetchInventory();
        closeModal("addModal");
    })
    .catch(error => console.error("Error adding item:", error));
}

function removeItem() {
let itemName = document.getElementById("removeName").value;
let itemQuantity = document.getElementById("removeQuantity").value;

fetch("/remove_item", {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify({
    name: itemName,
    quantity: parseInt(itemQuantity)
}),
})
.then(response => response.json())
.then(data => {
alert(data.message);
fetchInventory();
closeModal("removeModal");
})
.catch(error => console.error("Error removing item:", error));
}

function deleteItem() {
    let itemCode = document.getElementById("deleteItemCode").value;

    fetch("/delete_item", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_code: itemCode }),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        fetchInventory(); // Refresh inventory table
        closeModal("deleteModal");
    })
    .catch(error => console.error("Error deleting item:", error));
}

function confirmDelete(itemCode, itemName) {
    document.getElementById("deleteItemCode").value = itemCode;
    document.getElementById("deleteItemName").textContent = itemName;
    openModal("deleteModal");
}


function toggleDarkMode() {
    document.body.classList.toggle("dark-mode");
    
    // Store user preference in localStorage
    if (document.body.classList.contains("dark-mode")) {
        localStorage.setItem("darkMode", "enabled");
    } else {
        localStorage.setItem("darkMode", "disabled");
    }
}

// Apply dark mode on page load if it was enabled before
document.addEventListener("DOMContentLoaded", () => {
    if (localStorage.getItem("darkMode") === "enabled") {
        document.body.classList.add("dark-mode");
    }
});


function openModal(modalId) {
    document.getElementById(modalId).style.display = "flex";
    document.getElementById("modalOverlay").style.display = "block"; // Show overlay
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = "none";
    document.getElementById("modalOverlay").style.display = "none"; // Hide overlay
}

function openEditModal(itemCode, name, quantity, cost, profit) {
    document.getElementById("editCode").value = itemCode; // Hidden field for backend
    document.getElementById("editCodeDisplay").value = itemCode; // Visible but uneditable
    document.getElementById("editName").value = name;
    document.getElementById("editQuantity").value = quantity;
    document.getElementById("editCost").value = cost;
    document.getElementById("editProfit").value = profit;
    openModal("editModal");
}



function saveEdit() {
    let itemCode = document.getElementById("editCode").value;
    let itemName = document.getElementById("editName").value;
    let itemQuantity = document.getElementById("editQuantity").value;
    let itemCost = document.getElementById("editCost").value;
    let itemProfit = document.getElementById("editProfit").value;

    fetch("/edit_item", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            item_code: itemCode,
            name: itemName,
            quantity: parseInt(itemQuantity),
            cost: parseFloat(itemCost),
            profit: parseFloat(itemProfit)
        }),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        fetchInventory(); // Refresh inventory table
        closeModal("editModal");
    })
    .catch(error => console.error("Error updating item:", error));
}

function importInvoice() {
    let invoiceInput = document.getElementById("invoiceInput");
    let file = invoiceInput.files[0];

    if (!file) {
        alert("Please select an invoice image.");
        return;
    }

    let formData = new FormData();
    formData.append("invoice", file);

    fetch("/import_invoice", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        // Populate review table
        let tbody = document.querySelector("#importItemsTable");
        tbody.innerHTML = "";
        data.data.forEach((item, index) => {
            let row = `<tr>
                <td><input type="text" placeholder="Enter Item Code" id="item_code-${index}" /></td>
                <td contenteditable="true">${item.name}</td>
                <td contenteditable="true">${item.quantity}</td>
                <td contenteditable="true">${item.price}</td>
                <td><input type="text" placeholder="Enter Profit %" id="profit-${index}" /></td>
            </tr>`;
            tbody.innerHTML += row;
        });

        openModal("reviewModal");
    })
    .catch(error => console.error("Error importing invoice:", error));
}

function confirmImport() {
    let rows = document.querySelectorAll("#importItemsTable tr");
    console.log("Total rows found:", rows.length);  // Debugging

    if (rows.length === 0) {
        alert("No rows found! Is the table ID correct?");
        return;
    }

    let items = [];

    rows.forEach((row, index) => {
        console.log(`Row ${index} contents:`, row.innerHTML); // Print row data to check structure

        // let item_code = row.cells[0]?.innerText.trim(); 
        let item_code = row.cells[0]?.querySelector("input")?.value.trim();

        let name = row.cells[1]?.innerText.trim();
        let quantity = parseInt(row.cells[2]?.innerText.trim()) || 0;
        let price = parseFloat(row.cells[3]?.innerText.replace("$", "").trim()) || 0;
        let profitPercentage = parseFloat(document.getElementById(`profit-${index}`)?.value) || 0;

        console.log(`Parsed data for row ${index}:`, { item_code, name, quantity, price, profitPercentage });

        items.push({ item_code, name, quantity, price, profit_percentage: profitPercentage });
    });

    console.log("Final items array:", items); // Log what we’re actually sending

    if (items.length === 0) {
        alert("No valid items to import! Check the console for details.");
        return;
    }

    fetch("/confirm_import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Server response:", data);
        if (data.success) {
            alert("Import Confirmed!");
            closeModal();
        } else {
            alert("Error confirming import!");
        }
    })
    .catch(error => console.error("Fetch error:", error));
}


function populateImportTable(items) {
    let tableBody = document.getElementById("importItemsTable");
    tableBody.innerHTML = ""; // Clear previous content

    items.forEach((item, index) => {
        let row = document.createElement("tr");

        row.innerHTML = `
            <td>${item.name}</td>
            <td>${item.quantity}</td>
            <td>$${item.price.toFixed(2)}</td>
            <td>
                <input type="number" class="profit-input" 
                    id="profit-${index}" placeholder="Enter %" min="0">
            </td>
        `;

        tableBody.appendChild(row);
    });
}




// Fetch inventory on page load
document.addEventListener("DOMContentLoaded", fetchInventory);