# OCR Delivery Note Scanning — Guide for Factory Staff

**For: Anyone who receives goods and scans delivery notes**

---

## How It Works

When goods arrive at the factory, you scan or photograph the delivery note and drop the file into a shared Google Drive folder. The system reads it automatically using AI, extracts the supplier name, item descriptions, and quantities, and creates a record in ERPNext for the accounting team to process.

Nothing is posted or submitted automatically — the accounting team always reviews the data before creating any documents.

---

## Accepted File Types

- **PDF** — scanned delivery notes
- **JPEG** (.jpg) — photos taken with a phone camera
- **PNG** — screenshots or scanned images

Maximum file size: **10 MB**

**One delivery note per file.** Unlike invoices, the system expects each scan to contain a single delivery note.

---

## How to Submit a Delivery Note Scan

### Step 1: Scan or Photograph the Delivery Note

- **Best option:** Use the "Scan" feature in Google Drive (phone app) — this creates a clean, well-lit PDF
- **Also fine:** Take a regular photo with your phone camera (JPEG)
- Make sure the full document is visible, including the supplier name, item list, and quantities

### Step 2: Drop the File in Google Drive

1. Open the shared **OCR Delivery Notes** folder in Google Drive
2. Drop your file into the folder
3. That's it — the system checks the folder every 15 minutes

After processing, the file is automatically moved to an archive folder. A copy of the scan is also attached to any documents created from it, so you can always find the original.

#### Adding the Folder to Your Phone Home Screen

So you don't have to navigate through Drive every time:

**Android:**
1. Open the **Google Drive** app
2. Navigate to the shared **OCR Delivery Notes** folder
3. You should now be inside the folder (you'll see its contents, or it will be empty)
4. Tap the **three dots** menu in the top-right corner of the screen
5. Tap **Add to Home screen**
6. A shortcut icon appears on your home screen — tap it to go straight to the folder

**iPhone / iPad:**
1. Open the **Google Drive** app
2. Navigate to the shared **OCR Delivery Notes** folder
3. You should now be inside the folder
4. Tap the **three dots** menu in the top-right corner of the screen
5. Tap **Add to Home Screen** (on newer iOS) or **Copy link**, then open Safari, paste the link, tap the **Share** button, and tap **Add to Home Screen**
6. Name it something short like "DN Scans" and tap **Add**

Now you can scan a delivery note, tap the home screen shortcut, and upload — all in a few seconds.

---

## Tips for Good Scans

- **Flat and square** — lay the delivery note on a flat surface, photograph it straight on (not at an angle)
- **Good lighting** — avoid shadows and glare; natural light works best
- **Full page visible** — include all edges of the document, especially the supplier name and item list
- **One document per photo** — don't combine multiple delivery notes in a single photo
- **Use "Scan" if you can** — the scan feature in the Google Drive app automatically crops, straightens, and enhances the image

---

## What Happens After You Drop the File

The system:

1. **Reads the file** using AI — extracts the supplier name, delivery note number, date, and line items (descriptions, quantities, units of measure)
2. **Matches the supplier** to an existing supplier in ERPNext
3. **Matches each item** to existing items in ERPNext
4. **Creates an OCR Delivery Note record** in ERPNext for the accounting team

The accounting team then:

- Reviews the extracted data and corrects any mistakes
- Links it to an existing Purchase Order (if one exists)
- Creates either a **Purchase Receipt** (goods received) or a **Purchase Order** (if no PO existed for this delivery)

---

## Common Questions

**How long does processing take?**
Usually 5–30 seconds after the system picks up the file. Remember: the folder is checked every 15 minutes, so there may be a short wait before processing starts.

**What if I take a blurry photo?**
The AI will try its best, but blurry or poorly lit photos reduce accuracy. The accounting team will see a low confidence score and check the data more carefully. Use the "Scan" feature in Google Drive for best results.

**What if the supplier name isn't visible on the delivery note?**
The record will be created with the supplier marked as "Unmatched". The accounting team will identify the supplier manually.

**What if the delivery note has items not yet in ERPNext?**
The items will be listed with descriptions from the scan but marked as "Unmatched". The accounting team will handle matching or creating new items.

**Can I drop multiple files at once?**
Yes. Each file is processed separately.

**What if I accidentally scan something that isn't a delivery note?**
No problem — the accounting team can mark it as "No Action Required" with a reason (e.g., "packing slip", "duplicate scan"). Nothing will be created from it.

**Where does the original file go?**
After processing, the file is moved from the scan folder to an archive folder organised by year, month, and supplier. There's a "View Original Scan" link on each OCR Delivery Note record in ERPNext.
