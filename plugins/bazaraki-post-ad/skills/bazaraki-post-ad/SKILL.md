---
name: bazaraki-post-ad
description: >-
  Automates filling in a Bazaraki.com classified ad form (https://www.bazaraki.com/post_ad/).
  Use whenever the user wants to post, list, or advertise something for sale on Bazaraki.
  Trigger phrases: "put this on Bazaraki", "create a Bazaraki listing", "post ad on Bazaraki",
  "разместить на Базараки", "добавить объявление на Базараки", "Cyprus classifieds".
  Fills category, title, price, description, dropdowns, and WhatsApp automatically,
  then pauses at the Images section for manual photo upload (browser security blocks automation).
---

# Bazaraki Post Ad

Automates the Bazaraki.com "Post an Ad" form via JavaScript injection (Claude in Chrome).
Photos must be uploaded manually — everything else is automated.

## Prerequisites

- User is **logged in** to Bazaraki.com in Chrome
- Claude in Chrome extension is active

---

## Workflow

### Step 1 — Gather listing info

Collect from the user or from any description `.md` files they provide:

- **Title** — max 80 chars, no forbidden words: sale/urgent/sell/price/rent/inexpensively
- **Price** in €, negotiable yes/no
- **Category** — see Category Reference below
- **Condition** — Used or New
- **Description** — plain text, no phone/email; end with "Collection from [city]. Cash only."
- **WhatsApp** — enable? (usually yes)

---

### Step 2 — Navigate

Go to `https://www.bazaraki.com/post_ad/`

---

### Step 3 — Select category (3 levels, separate JS calls)

```javascript
// Click each level one at a time — do NOT use setTimeout, use separate JS calls
Array.from(document.querySelectorAll('[data-rubric-id]'))
  .find(e => e.dataset.rubricId === 'LEVEL1_ID' && e.offsetParent !== null)?.click();
```

Repeat for Level 2 and Level 3. Verify the leaf element has class `--selected`, then click Continue:

```javascript
// ⚠️ Use getComputedStyle — NOT offsetParent — to find the visible Continue button
Array.from(document.querySelectorAll('button'))
  .find(b => b.textContent.trim() === 'Continue' &&
    window.getComputedStyle(b).display !== 'none')?.click();
```

**Category Reference:**

| Item | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| Sofa / Living room | 663 | 13 (Furniture) | 2241 (Dining, living room furniture) |
| Coffee / side table | 663 | 13 | 2241 |
| Desk / Office | 663 | 13 | 2683 (Desks for home & office) |
| Bedroom | 663 | 13 | 2243 (Beds, bedroom furniture) |
| Bookcase | 663 | 13 | 2688 (Bookcase & CD shelves) |
| Other furniture | 663 | 13 | 103 (Other furniture) |
| Garden furniture | 663 | 14 (Garden, patio) | — |
| Kids furniture | 7 (Kids' stuff) | 60 (Furniture) | 3112 (Other) |

---

### Step 4 — Set location

```javascript
document.querySelector('.item__location-popup.--profile')?.click();
// Verify: document.querySelector('input[name="location"]')?.value  // "413" = Limassol–Ypsonas
```

---

### Step 5 — Fill title ⚠️ IFRAME TRICK

The title field is a rich-text editor inside an `<iframe>` — **not** a standard input.
Setting `textarea[name="title"]` value does nothing (it's off-screen at x=-9999px).

```javascript
const iframe = document.querySelector('.js-title-codemirror iframe');
const body = iframe?.contentDocument?.body;
if (body) {
  body.textContent = 'YOUR TITLE HERE';
  ['input', 'keyup', 'change'].forEach(evt =>
    body.dispatchEvent(new Event(evt, {bubbles: true}))
  );
}
```

---

### Step 6 — Fill price, negotiable, description, WhatsApp (one JS call)

```javascript
const price = document.querySelector('input[name="price"]');
price.value = '250';
['input','change'].forEach(e => price.dispatchEvent(new Event(e, {bubbles:true})));

const neg = document.getElementById('negotiable_price');
if (neg && !neg.checked) neg.click();

const desc = document.querySelector('textarea[name="description"]');
desc.value = `DESCRIPTION TEXT HERE`;
['input','change'].forEach(e => desc.dispatchEvent(new Event(e, {bubbles:true})));

const wa = document.getElementById('show_contacts_whatsapp');
if (wa && !wa.checked) wa.click();
```

---

### Step 7 — Fill custom dropdowns

Bazaraki uses custom JS dropdowns (not native `<select>`). Always inspect first:

```javascript
const dropdowns = Array.from(document.querySelectorAll('.js-dropdown.dd-block'))
  .filter(d => d.offsetParent !== null);

// Inspect all options
dropdowns.map((d, i) => ({
  index: i,
  label: d.querySelector('.dd-label')?.textContent?.trim(),
  items: Array.from(d.querySelectorAll('.js-dd-item')).map(li => li.textContent.trim())
}))

// Select an option
Array.from(dropdowns[INDEX].querySelectorAll('.js-dd-item'))
  .find(li => li.textContent.trim() === 'OPTION_TEXT')?.click();
```

⚠️ Selecting one dropdown may reveal a sub-dropdown — always re-inspect after each selection.

---

### Step 8 — Verify

```javascript
({
  title:     document.querySelector('.js-title-codemirror iframe')?.contentDocument?.body?.textContent,
  price:     document.querySelector('input[name="price"]')?.value,
  location:  document.querySelector('input[name="location"]')?.value,
  dropdowns: Array.from(document.querySelectorAll('.js-dropdown.dd-block'))
               .filter(d => d.offsetParent !== null)
               .map(d => d.querySelector('.dd-label')?.textContent?.trim()),
  whatsapp:  document.getElementById('show_contacts_whatsapp')?.checked,
  negotiable: document.getElementById('negotiable_price')?.checked,
})
```

All dropdowns must show real values (not "Choose one...").

---

### Step 9 — Pause for photos ⏸️

Chrome blocks programmatic file upload. Scroll to the images section:

```javascript
Array.from(document.querySelectorAll('.form-group, .grey.place'))
  .find(g => g.textContent.includes('Images:') && g.offsetParent !== null)
  ?.scrollIntoView({behavior: 'smooth', block: 'center'});
```

Tell the user: "✅ All fields filled! Please upload photos, then confirm here."

---

### Step 10 — Submit

After user confirms photos are uploaded, scroll to and ask user to click **"Post an ad"**:

```javascript
document.querySelector('input[type="submit"], button[type="submit"]')
  ?.scrollIntoView({behavior: 'smooth', block: 'center'});
```

---

## Multiple listings

After each ad is posted, navigate back to `https://www.bazaraki.com/post_ad/` and start from Step 3.
Keep the user updated: "Ad 2/5 — starting now..."
