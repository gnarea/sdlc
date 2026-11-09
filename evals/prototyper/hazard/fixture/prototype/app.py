from flask import Flask, abort, render_template_string

from orders import find_order, load_orders

app = Flask(__name__)

ORDER_LIST = """
<h1>Orders due today</h1>
<ul>
{% for order in orders %}
  <li><a href="/orders/{{ order.id }}">{{ order.id }}</a>: {{ order.customer }}</li>
{% endfor %}
</ul>
"""

ORDER_PAGE = """
<h1>Order {{ order.id }} for {{ order.customer }}</h1>
<ol>
{% for step in order.steps %}
  <li>{{ step.name }}: {{ step.at or "pending" }}</li>
{% endfor %}
</ol>
<p>Van: {{ order.van or "not assigned yet" }}</p>
<p>Estimated arrival: {{ order.eta or "unknown" }}</p>
<p>Proof of delivery: {{ order.proof_of_delivery or "none yet" }}</p>
"""


@app.get("/")
def index():
    return render_template_string(ORDER_LIST, orders=load_orders())


@app.get("/orders/<order_id>")
def order(order_id: str):
    found = find_order(order_id)
    if found is None:
        abort(404)
    return render_template_string(ORDER_PAGE, order=found)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
