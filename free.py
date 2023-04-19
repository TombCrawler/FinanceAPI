# try:
#     symbol = request.form.get("symbol")
#     API = lookup(symbol)
#     price = API["price"]
#     price = float(price)
#     totalPrice = price * shares
#     if totalPrice > cashLeft
#         db.execute("INSERT INTO stocks ( price) VALUES(?)", price)
#                 return redirect("/")

#  except TypeError:
#     return apology("Symbol Not Found or Invalid Shares")