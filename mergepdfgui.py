import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pypdf import PdfReader, PdfWriter
from PIL import Image

desktop = os.path.join(os.path.expanduser("~"), "Desktop")

rows=[]

def parse_pages(text):
    result=[]
    for part in text.split(","):
        part=part.strip()
        if "-" in part:
            s,e=part.split("-")
            for i in range(int(s),int(e)+1):
                result.append(i)
        else:
            result.append(int(part))
    return result


def add_pdf():

    path=filedialog.askopenfilename(filetypes=[("PDF","*.pdf")])
    if not path:
        return

    reader=PdfReader(path)
    total=len(reader.pages)

    add_row(path,"PDF",total)


def add_image():

    path=filedialog.askopenfilename(
        filetypes=[("Images","*.png *.jpg *.jpeg *.bmp *.webp *.tiff")]
    )
    if not path:
        return

    add_row(path,"IMG",1)


def add_row(path,typ,total):

    r=len(rows)+1

    frame=tk.Frame(table)
    frame.grid(row=r,column=0,columnspan=5,sticky="nsew")

    def open_file(e):
        os.startfile(path)

    file_lbl=tk.Label(frame,text=os.path.basename(path),bd=1,relief="solid",width=35)
    file_lbl.grid(row=0,column=0,sticky="nsew")
    file_lbl.bind("<Double-1>",open_file)

    type_lbl=tk.Label(frame,text=typ,bd=1,relief="solid",width=6)
    type_lbl.grid(row=0,column=1)

    total_lbl=tk.Label(frame,text=str(total),bd=1,relief="solid",width=10)
    total_lbl.grid(row=0,column=2)

    page_entry=tk.Entry(frame,bd=1,relief="solid",width=20)
    page_entry.grid(row=0,column=3)

    if typ=="IMG":
        page_entry.insert(0,"1")
        page_entry.config(state="disabled")

    def add_all():
        page_entry.delete(0,"end")
        page_entry.insert(0,f"1-{total}")

    btn=tk.Button(frame,text="Add All",command=add_all,width=10)
    btn.grid(row=0,column=4)

    rows.append({
        "type":typ,
        "path":path,
        "pages":page_entry,
        "total":total
    })


def remove_selected():

    if not rows:
        return

    rows.pop()

    for widget in table.grid_slaves():
        if int(widget.grid_info()["row"])==len(rows)+1:
            widget.destroy()


def merge():

    name=output_entry.get().strip()

    if name=="":
        messagebox.showerror("Error","Enter output name")
        return

    if not name.endswith(".pdf"):
        name+=".pdf"

    writer=PdfWriter()

    for r in rows:

        if r["type"]=="IMG":

            img=Image.open(r["path"]).convert("RGB")

            tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".pdf")

            img.save(tmp.name)

            reader=PdfReader(tmp.name)

            writer.add_page(reader.pages[0])

        else:

            text=r["pages"].get()

            if text=="":
                continue

            reader=PdfReader(r["path"])

            pages=parse_pages(text)

            for p in pages:
                writer.add_page(reader.pages[p-1])

    out=os.path.join(desktop,name)

    with open(out,"wb") as f:
        writer.write(f)

    messagebox.showinfo("Done",f"Saved to:\n{out}")


root=tk.Tk()
root.title("PDF Merge Tool")
root.geometry("820x450")


toolbar=tk.Frame(root,bg="#ddd")
toolbar.pack(fill="x")

tk.Button(toolbar,text="Add PDF",command=add_pdf).pack(side="left",padx=4,pady=4)
tk.Button(toolbar,text="Add Image",command=add_image).pack(side="left",padx=4)
tk.Button(toolbar,text="Remove Last",command=remove_selected).pack(side="left",padx=4)
tk.Button(toolbar,text="Merge",command=merge).pack(side="right",padx=4)


table=tk.Frame(root)
table.pack(pady=10)


headers=["File Name","Type","Total Pages","Pages","Add All"]

for i,h in enumerate(headers):
    tk.Label(table,text=h,bd=2,relief="solid",width=20).grid(row=0,column=i)


bottom=tk.Frame(root)
bottom.pack(pady=10)

tk.Label(bottom,text="Output name").pack(side="left")

output_entry=tk.Entry(bottom,width=25)
output_entry.pack(side="left",padx=5)


root.mainloop()