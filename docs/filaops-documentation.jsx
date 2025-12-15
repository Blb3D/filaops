import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Book, Settings, Package, ShoppingCart, Factory, Truck, BarChart3, Shield, Users, Workflow, Database, AlertTriangle, CheckCircle2, FileText, Layers, Boxes, ClipboardList, Calculator, Link } from 'lucide-react';

const FilaOpsDocumentation = () => {
  const [activeSection, setActiveSection] = useState('overview');
  const [expandedSops, setExpandedSops] = useState({});

  const toggleSop = (id) => {
    setExpandedSops(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const sections = [
    { id: 'overview', label: 'System Overview', icon: Book },
    { id: 'workflows', label: 'Business Workflows', icon: Workflow },
    { id: 'products', label: 'Products & Catalog', icon: Package },
    { id: 'bom', label: 'Bill of Materials', icon: Layers },
    { id: 'inventory', label: 'Inventory Management', icon: Boxes },
    { id: 'sales', label: 'Sales Orders', icon: ShoppingCart },
    { id: 'production', label: 'Production Orders', icon: Factory },
    { id: 'mrp', label: 'MRP Planning', icon: Calculator },
    { id: 'traceability', label: 'Traceability', icon: Shield },
    { id: 'integrations', label: 'Integrations', icon: Link },
    { id: 'admin', label: 'Administration', icon: Settings },
  ];

  const SopStep = ({ number, title, description, notes, warning }) => (
    <div className="ml-4 mb-4 border-l-2 border-blue-200 pl-4">
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">
          {number}
        </span>
        <div className="flex-1">
          <h5 className="font-semibold text-gray-800">{title}</h5>
          <p className="text-gray-600 text-sm mt-1">{description}</p>
          {notes && (
            <div className="mt-2 p-2 bg-blue-50 rounded text-sm text-blue-800">
              <strong>Note:</strong> {notes}
            </div>
          )}
          {warning && (
            <div className="mt-2 p-2 bg-amber-50 rounded text-sm text-amber-800 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{warning}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const SopSection = ({ id, title, purpose, scope, steps, qualityChecks }) => (
    <div className="border rounded-lg mb-4 overflow-hidden">
      <button
        onClick={() => toggleSop(id)}
        className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          <span className="font-semibold text-gray-800">{title}</span>
        </div>
        {expandedSops[id] ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
      </button>
      {expandedSops[id] && (
        <div className="p-4 border-t">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="p-3 bg-green-50 rounded">
              <h5 className="font-semibold text-green-800 text-sm">Purpose</h5>
              <p className="text-green-700 text-sm mt-1">{purpose}</p>
            </div>
            <div className="p-3 bg-purple-50 rounded">
              <h5 className="font-semibold text-purple-800 text-sm">Scope</h5>
              <p className="text-purple-700 text-sm mt-1">{scope}</p>
            </div>
          </div>
          <h5 className="font-semibold text-gray-800 mb-3">Procedure</h5>
          {steps.map((step, idx) => (
            <SopStep key={idx} number={idx + 1} {...step} />
          ))}
          {qualityChecks && (
            <div className="mt-4 p-3 bg-emerald-50 rounded">
              <h5 className="font-semibold text-emerald-800 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" /> Quality Checks
              </h5>
              <ul className="mt-2 space-y-1">
                {qualityChecks.map((check, idx) => (
                  <li key={idx} className="text-emerald-700 text-sm flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    {check}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderContent = () => {
    switch (activeSection) {
      case 'overview':
        return (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg p-6 text-white">
              <h2 className="text-2xl font-bold mb-2">FilaOps ERP System</h2>
              <p className="opacity-90">Production-grade manufacturing resource planning for 3D print operations</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold text-gray-800 mb-2">Document Info</h4>
                <p className="text-sm text-gray-600">Version: 1.0</p>
                <p className="text-sm text-gray-600">Last Updated: December 2025</p>
                <p className="text-sm text-gray-600">Owner: BLB3D Printing</p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold text-gray-800 mb-2">Compliance Ready</h4>
                <p className="text-sm text-gray-600">• ISO 13485 (Medical Devices)</p>
                <p className="text-sm text-gray-600">• FDA 21 CFR 820</p>
                <p className="text-sm text-gray-600">• AS9100 (Aerospace)</p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold text-gray-800 mb-2">Tech Stack</h4>
                <p className="text-sm text-gray-600">• Backend: Python/FastAPI</p>
                <p className="text-sm text-gray-600">• Database: SQL Server</p>
                <p className="text-sm text-gray-600">• API: RESTful JSON</p>
              </div>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">System Architecture</h3>
              <div className="bg-gray-50 p-4 rounded font-mono text-sm overflow-x-auto">
                <pre>{`┌─────────────────────────────────────────────────────────────┐
│                     Order Sources                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Squarespace   │  Customer Portal │    B2B Partners        │
│   (Retail)      │   (Custom Quotes)│   (Wholesale)          │
└────────┬────────┴────────┬────────┴────────┬────────────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FilaOps ERP                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Products │ │   BOMs   │ │ Orders   │ │Production│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Inventory │ │ Routing  │ │Traceabil │ │   MRP    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Print Floor                               │
│         (Bambu, Prusa, or any 3D printer fleet)             │
└─────────────────────────────────────────────────────────────┘`}</pre>
              </div>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Core Modules</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[
                  { name: 'Products & Catalog', desc: 'SKUs, variants, pricing with material-aware costing' },
                  { name: 'Bill of Materials', desc: 'Multi-level BOMs with filament/hardware components' },
                  { name: 'Inventory Management', desc: 'Real-time stock levels, FIFO tracking, alerts' },
                  { name: 'Sales Orders', desc: 'Multi-channel order management' },
                  { name: 'Production Orders', desc: 'Manufacturing workflow with operation tracking' },
                  { name: 'MRP', desc: 'Material requirements planning with forecasting' },
                  { name: 'Work Centers', desc: 'Machine pools, capacity planning, utilization' },
                  { name: 'Traceability', desc: 'Serial/lot tracking, recall queries (FDA/ISO)' },
                ].map((mod, idx) => (
                  <div key={idx} className="p-3 bg-gray-50 rounded">
                    <h5 className="font-semibold text-gray-800">{mod.name}</h5>
                    <p className="text-sm text-gray-600">{mod.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case 'workflows':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Business Workflows</h2>
            
            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Quote-to-Cash Process Flow</h3>
              <div className="flex flex-wrap items-center justify-center gap-2 p-4 bg-gray-50 rounded">
                {['Quote Request', 'Quote Created', 'Quote Approved', 'Sales Order', 'Production Order', 'Manufacturing', 'QC Inspection', 'Shipping', 'Invoice'].map((step, idx) => (
                  <React.Fragment key={idx}>
                    <div className="px-3 py-2 bg-blue-600 text-white rounded text-sm font-medium">
                      {step}
                    </div>
                    {idx < 8 && <ChevronRight className="w-5 h-5 text-gray-400" />}
                  </React.Fragment>
                ))}
              </div>
            </div>

            <SopSection
              id="workflow-quote"
              title="SOP-WF-001: Quote Processing Workflow"
              purpose="Define the standard process for handling customer quote requests from receipt through approval."
              scope="All incoming quote requests via portal, email, or phone."
              steps={[
                { title: 'Receive Quote Request', description: 'Customer submits request via portal or email. System auto-generates quote number (Q-YYYY-XXXX format).' },
                { title: 'Review Requirements', description: 'Verify file formats (STL, 3MF), quantities, material requirements, and delivery timeline.', notes: 'For multi-material 3MF files, ensure AMS color mapping is included.' },
                { title: 'Calculate Pricing', description: 'System calculates material costs, print time estimates, and labor. Apply customer-specific pricing tiers if applicable.' },
                { title: 'Generate Quote Document', description: 'Create formal quote with itemized pricing, lead times, and terms. Include material specifications.' },
                { title: 'Internal Review', description: 'For quotes >$1,000 or new customers, route for manager approval.', warning: 'Custom tooling or rush orders require engineering sign-off.' },
                { title: 'Send to Customer', description: 'Email quote with expiration date (typically 30 days). Log customer communication.' },
                { title: 'Follow-Up', description: 'If no response in 7 days, send follow-up. Update quote status accordingly.' },
              ]}
              qualityChecks={[
                'All required files attached and validated',
                'Pricing matches current material costs + margin targets',
                'Lead time is achievable based on current capacity',
                'Customer contact information verified',
              ]}
            />

            <SopSection
              id="workflow-order"
              title="SOP-WF-002: Order Fulfillment Workflow"
              purpose="Standardize the process from order receipt through production scheduling."
              scope="All confirmed sales orders regardless of channel (retail, wholesale, custom)."
              steps={[
                { title: 'Order Confirmation', description: 'Upon payment/PO receipt, convert quote to sales order. System generates SO number (SO-YYYY-XXXX).' },
                { title: 'Inventory Check', description: 'System performs automatic inventory allocation. Reserved stock updated.', notes: 'FIFO allocation applies for lot-tracked materials.' },
                { title: 'BOM Explosion', description: 'For manufactured items, system explodes BOM to determine component requirements.' },
                { title: 'Material Availability', description: 'Verify all components available or trigger purchase requisitions for shortages.' },
                { title: 'Create Production Order', description: 'Generate production order(s) linked to sales order. Assign to work center queue.', warning: 'Rush orders (< 3 day lead time) require supervisor override.' },
                { title: 'Schedule Production', description: 'Production order enters scheduling queue. MRP considers capacity and material availability.' },
                { title: 'Customer Notification', description: 'Send order confirmation email with estimated ship date.' },
              ]}
              qualityChecks={[
                'Payment verified or valid PO on file',
                'All SKUs exist and are active',
                'Shipping address validated',
                'Production capacity confirmed',
              ]}
            />

            <SopSection
              id="workflow-production"
              title="SOP-WF-003: Production Execution Workflow"
              purpose="Define the manufacturing process from job release through completion."
              scope="All production orders for printed parts and assemblies."
              steps={[
                { title: 'Job Release', description: 'Production supervisor releases jobs to floor. Operators see queue in work center dashboard.' },
                { title: 'Material Staging', description: 'Pull required filament lots from inventory. Scan lot barcodes to link to production order.', notes: 'For traceability, lot consumption must be recorded before print start.' },
                { title: 'Printer Setup', description: 'Load correct filament, verify nozzle size, apply bed adhesive. Record printer serial number.' },
                { title: 'Print Execution', description: 'Start print job. Monitor first layer adhesion. Log any anomalies or failures.' },
                { title: 'Post-Processing', description: 'Remove supports, clean bed marks, perform any required finishing operations.' },
                { title: 'QC Inspection', description: 'Inspect against dimensional tolerances and visual standards. Record pass/fail.', warning: 'For regulated products (medical/aerospace), document all measurements.' },
                { title: 'Serial Assignment', description: 'For serialized products, generate and apply serial number label.' },
                { title: 'Complete Operation', description: 'Mark production order complete. Finished goods move to inventory.' },
              ]}
              qualityChecks={[
                'Correct material lot consumed and recorded',
                'Print completed without intervention (or failure documented)',
                'Dimensional inspection passed (if required)',
                'Serial number applied and recorded (if serialized)',
                'Parts match quantity ordered',
              ]}
            />

            <SopSection
              id="workflow-ship"
              title="SOP-WF-004: Shipping Workflow"
              purpose="Standardize packing, labeling, and carrier handoff procedures."
              scope="All outbound shipments from production facility."
              steps={[
                { title: 'Pick List Generation', description: 'System generates pick list when all SO lines are ready. Pick list shows bin locations.' },
                { title: 'Order Picking', description: 'Warehouse pulls items from finished goods inventory. Scan barcodes to verify correct items.' },
                { title: 'Packing', description: 'Pack items per customer requirements. Use appropriate void fill and protection.', notes: 'Fragile or precision parts require specific packing protocols.' },
                { title: 'Documentation', description: 'Include packing slip, CoC (if required), and any customer-requested docs.' },
                { title: 'Rate Shopping', description: 'System retrieves rates from EasyPost. Select carrier based on cost/speed requirements.' },
                { title: 'Label Generation', description: 'Generate shipping label. Apply to package. Record tracking number.' },
                { title: 'Carrier Handoff', description: 'Place packages in carrier staging area. Confirm pickup or drop-off.' },
                { title: 'Customer Notification', description: 'System sends automated ship notification with tracking info.' },
              ]}
              qualityChecks={[
                'All items scanned match pick list',
                'Package weight reasonable for contents',
                'Shipping label matches order address',
                'Tracking number recorded in system',
              ]}
            />
          </div>
        );

      case 'products':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Products & Catalog Management</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">The Products module manages your catalog of manufactured goods, purchased components, and raw materials. Each product has a unique SKU, pricing configuration, and can be linked to a Bill of Materials for cost calculation.</p>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Product Types</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-3 bg-green-50 rounded">
                  <h5 className="font-semibold text-green-800">Manufactured</h5>
                  <p className="text-sm text-green-700 mt-1">Items produced in-house via 3D printing or assembly. Have BOMs and routings.</p>
                </div>
                <div className="p-3 bg-purple-50 rounded">
                  <h5 className="font-semibold text-purple-800">Purchased</h5>
                  <p className="text-sm text-purple-700 mt-1">Components and hardware bought from suppliers. Tracked in inventory.</p>
                </div>
                <div className="p-3 bg-amber-50 rounded">
                  <h5 className="font-semibold text-amber-800">Raw Material</h5>
                  <p className="text-sm text-amber-700 mt-1">Filament, resin, and consumables. Lot-tracked for traceability.</p>
                </div>
              </div>
            </div>

            <SopSection
              id="prod-create"
              title="SOP-PROD-001: Creating a New Product"
              purpose="Establish standard procedure for adding new products to the catalog."
              scope="All new SKUs including manufactured items, purchased components, and raw materials."
              steps={[
                { title: 'Determine Product Type', description: 'Identify if item is Manufactured, Purchased, or Raw Material. This affects required fields.' },
                { title: 'Generate SKU', description: 'Follow SKU naming convention: [Category]-[Material]-[Variant]-[Rev]. Example: PRD-PLA-RED-A', notes: 'SKUs must be unique. System prevents duplicates.' },
                { title: 'Enter Basic Info', description: 'Name, description, unit of measure, weight, dimensions. Add searchable tags.' },
                { title: 'Configure Pricing', description: 'Set standard cost, list price, and any customer-specific pricing tiers.' },
                { title: 'Set Inventory Parameters', description: 'Safety stock level, reorder point, lead time, preferred bin location.' },
                { title: 'Upload Assets', description: 'Add product images, STL/3MF files (for manufactured), spec sheets.' },
                { title: 'Activate Product', description: 'Set status to Active. Product now available for orders.' },
              ]}
              qualityChecks={[
                'SKU follows naming convention',
                'Pricing covers material + labor + margin',
                'Inventory parameters set (especially safety stock)',
                'At least one product image uploaded',
              ]}
            />

            <SopSection
              id="prod-pricing"
              title="SOP-PROD-002: Product Pricing Configuration"
              purpose="Define how product costs and selling prices are calculated and maintained."
              scope="All active products in the catalog."
              steps={[
                { title: 'Calculate Material Cost', description: 'For manufactured items, this flows from BOM. Sum component costs × quantities.' },
                { title: 'Add Labor Cost', description: 'Print time × machine rate + post-processing labor estimate.' },
                { title: 'Apply Overhead', description: 'Standard overhead percentage (typically 15-25%) for facility costs.' },
                { title: 'Set Target Margin', description: 'Apply margin target based on product category and customer segment.', notes: 'Retail typically 40-60%, Wholesale 20-35%, Custom 30-50%.' },
                { title: 'Configure Price Breaks', description: 'Set volume discounts if applicable. Define quantity thresholds and discount %.' },
                { title: 'Review Competitiveness', description: 'Compare to market pricing. Adjust margin if needed to remain competitive.' },
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">API Reference</h3>
              <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto">
                <div className="space-y-2">
                  <p className="text-green-400"># List all products</p>
                  <p>GET /api/v1/products</p>
                  <p className="text-green-400 mt-4"># Create new product</p>
                  <p>POST /api/v1/products</p>
                  <p className="text-gray-400">{"{"}</p>
                  <p className="text-gray-400 ml-4">"sku": "PRD-PLA-RED-A",</p>
                  <p className="text-gray-400 ml-4">"name": "Red PLA Widget",</p>
                  <p className="text-gray-400 ml-4">"product_type": "manufactured",</p>
                  <p className="text-gray-400 ml-4">"unit_price": 24.99</p>
                  <p className="text-gray-400">{"}"}</p>
                  <p className="text-green-400 mt-4"># Get product by ID</p>
                  <p>GET /api/v1/products/{"{id}"}</p>
                  <p className="text-green-400 mt-4"># Update product</p>
                  <p>PATCH /api/v1/products/{"{id}"}</p>
                </div>
              </div>
            </div>
          </div>
        );

      case 'bom':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Bill of Materials (BOM)</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">The BOM module defines the components, materials, and quantities required to manufacture each product. FilaOps supports multi-level BOMs, allowing sub-assemblies to have their own component structures.</p>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">BOM Component Types</h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                  <div className="w-10 h-10 bg-orange-500 rounded flex items-center justify-center">
                    <span className="text-white text-lg">🧵</span>
                  </div>
                  <div>
                    <h5 className="font-semibold">Filament</h5>
                    <p className="text-sm text-gray-600">Primary material. Quantity in grams. Links to filament lot for traceability.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                  <div className="w-10 h-10 bg-gray-500 rounded flex items-center justify-center">
                    <span className="text-white text-lg">🔩</span>
                  </div>
                  <div>
                    <h5 className="font-semibold">Hardware</h5>
                    <p className="text-sm text-gray-600">Screws, nuts, inserts, magnets, etc. Quantity in pieces.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                  <div className="w-10 h-10 bg-blue-500 rounded flex items-center justify-center">
                    <span className="text-white text-lg">📦</span>
                  </div>
                  <div>
                    <h5 className="font-semibold">Sub-Assembly</h5>
                    <p className="text-sm text-gray-600">Another manufactured item used as a component. Enables multi-level BOMs.</p>
                  </div>
                </div>
              </div>
            </div>

            <SopSection
              id="bom-create"
              title="SOP-BOM-001: Creating a Bill of Materials"
              purpose="Define the procedure for creating accurate BOMs that support costing and production."
              scope="All manufactured products requiring component tracking."
              steps={[
                { title: 'Identify Parent Product', description: 'Select or create the finished good SKU that this BOM applies to.' },
                { title: 'List All Components', description: 'Enumerate every material, part, and sub-assembly. Include packaging if tracked.' },
                { title: 'Determine Quantities', description: 'For filament, use actual print weight + 5% waste factor. For hardware, use exact counts.', notes: 'Run test prints to validate filament consumption estimates.' },
                { title: 'Add Components to BOM', description: 'Enter each component with SKU, quantity per unit, and unit of measure.' },
                { title: 'Set Component Type', description: 'Mark each line as Filament, Hardware, or Sub-Assembly for proper handling.' },
                { title: 'Calculate Rolled-Up Cost', description: 'System sums component costs to calculate total material cost.' },
                { title: 'Review and Approve', description: 'Engineering review for accuracy. Mark BOM as Active.' },
              ]}
              qualityChecks={[
                'All components exist as active products',
                'Filament quantities validated against actual prints',
                'Hardware counts match assembly instructions',
                'Rolled-up cost appears reasonable',
              ]}
            />

            <SopSection
              id="bom-rev"
              title="SOP-BOM-002: BOM Revision Control"
              purpose="Maintain version control for BOM changes to support traceability."
              scope="Any modifications to existing BOMs."
              steps={[
                { title: 'Identify Change Needed', description: 'Document what needs to change: component swap, quantity adjustment, or new part.' },
                { title: 'Create ECO', description: 'For significant changes, create Engineering Change Order documenting reason and impact.', notes: 'Minor adjustments (< 5% qty change) may skip ECO.' },
                { title: 'Create New Revision', description: 'Copy current BOM to new revision (A→B, B→C, etc.). Never edit active revision directly.' },
                { title: 'Apply Changes', description: 'Modify component list on draft revision. Update quantities, swap components.' },
                { title: 'Recalculate Costs', description: 'System recalculates rolled-up cost. Review pricing impact.' },
                { title: 'Approve Revision', description: 'Engineering sign-off. Set effectivity date.' },
                { title: 'Activate New Revision', description: 'Make new revision Active. Previous becomes Historical.' },
              ]}
              qualityChecks={[
                'ECO documented (if required)',
                'Previous revision marked Historical',
                'Pricing updated to reflect cost change',
                'Production notified of change',
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Example BOM Structure</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="text-left p-2">Level</th>
                      <th className="text-left p-2">Component SKU</th>
                      <th className="text-left p-2">Description</th>
                      <th className="text-right p-2">Qty</th>
                      <th className="text-left p-2">UOM</th>
                      <th className="text-right p-2">Unit Cost</th>
                      <th className="text-right p-2">Ext Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b bg-blue-50">
                      <td className="p-2 font-semibold">0</td>
                      <td className="p-2 font-semibold">FG-WIDGET-001</td>
                      <td className="p-2 font-semibold">Complete Widget Assembly</td>
                      <td className="p-2 text-right">1</td>
                      <td className="p-2">EA</td>
                      <td className="p-2 text-right">—</td>
                      <td className="p-2 text-right font-semibold">$12.45</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 pl-4">1</td>
                      <td className="p-2">FIL-PLA-BLK</td>
                      <td className="p-2">Black PLA Filament</td>
                      <td className="p-2 text-right">45</td>
                      <td className="p-2">g</td>
                      <td className="p-2 text-right">$0.025</td>
                      <td className="p-2 text-right">$1.13</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 pl-4">1</td>
                      <td className="p-2">FIL-PLA-RED</td>
                      <td className="p-2">Red PLA Filament</td>
                      <td className="p-2 text-right">12</td>
                      <td className="p-2">g</td>
                      <td className="p-2 text-right">$0.028</td>
                      <td className="p-2 text-right">$0.34</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 pl-4">1</td>
                      <td className="p-2">HW-M3-8MM</td>
                      <td className="p-2">M3x8mm Socket Cap Screw</td>
                      <td className="p-2 text-right">4</td>
                      <td className="p-2">EA</td>
                      <td className="p-2 text-right">$0.12</td>
                      <td className="p-2 text-right">$0.48</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 pl-4">1</td>
                      <td className="p-2">HW-INSERT-M3</td>
                      <td className="p-2">M3 Heat-Set Insert</td>
                      <td className="p-2 text-right">4</td>
                      <td className="p-2">EA</td>
                      <td className="p-2 text-right">$0.08</td>
                      <td className="p-2 text-right">$0.32</td>
                    </tr>
                    <tr>
                      <td className="p-2 pl-4">1</td>
                      <td className="p-2">SUB-BASE-001</td>
                      <td className="p-2">Widget Base Sub-Assembly</td>
                      <td className="p-2 text-right">1</td>
                      <td className="p-2">EA</td>
                      <td className="p-2 text-right">$10.18</td>
                      <td className="p-2 text-right">$10.18</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      case 'inventory':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Inventory Management</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">Inventory Management tracks stock levels across warehouses and bins, manages lot/serial numbers for traceability, and triggers alerts when stock falls below reorder points. FIFO (First-In-First-Out) consumption is enforced for lot-tracked materials.</p>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Inventory Concepts</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3 border rounded">
                  <h5 className="font-semibold text-gray-800">On-Hand Quantity</h5>
                  <p className="text-sm text-gray-600">Total physical inventory in warehouse, regardless of allocation.</p>
                </div>
                <div className="p-3 border rounded">
                  <h5 className="font-semibold text-gray-800">Available Quantity</h5>
                  <p className="text-sm text-gray-600">On-Hand minus Reserved. What can be promised to new orders.</p>
                </div>
                <div className="p-3 border rounded">
                  <h5 className="font-semibold text-gray-800">Reserved Quantity</h5>
                  <p className="text-sm text-gray-600">Allocated to confirmed sales orders awaiting production/shipment.</p>
                </div>
                <div className="p-3 border rounded">
                  <h5 className="font-semibold text-gray-800">Safety Stock</h5>
                  <p className="text-sm text-gray-600">Minimum level to maintain. Alerts trigger below this point.</p>
                </div>
              </div>
            </div>

            <SopSection
              id="inv-receive"
              title="SOP-INV-001: Receiving Inventory"
              purpose="Ensure accurate receipt of purchased materials with proper lot tracking."
              scope="All incoming shipments of purchased components and raw materials."
              steps={[
                { title: 'Verify Purchase Order', description: 'Match incoming shipment to open PO. Confirm vendor and expected items.' },
                { title: 'Physical Inspection', description: 'Check for shipping damage. Count items against packing slip.', warning: 'Report discrepancies immediately. Do not receive damaged goods without documentation.' },
                { title: 'Create Receipt', description: 'In FilaOps, navigate to Inventory > Receive. Select PO number.' },
                { title: 'Enter Lot Numbers', description: 'For lot-tracked items (filament), record manufacturer lot number and expiration (if applicable).', notes: 'Filament lots should include brand, color, and purchase date in lot ID.' },
                { title: 'Specify Bin Location', description: 'Assign storage location. System suggests default bin from product setup.' },
                { title: 'Post Receipt', description: 'Confirm receipt. System updates on-hand quantities and closes PO line.' },
                { title: 'Label Items', description: 'Apply internal barcode labels linking to lot number for scanning.' },
              ]}
              qualityChecks={[
                'Quantity received matches packing slip',
                'Lot number recorded for tracked items',
                'Items stored in correct bin location',
                'PO line properly closed',
              ]}
            />

            <SopSection
              id="inv-adjust"
              title="SOP-INV-002: Inventory Adjustments"
              purpose="Document the procedure for correcting inventory discrepancies."
              scope="Any inventory changes not from normal transactions (receive, ship, produce)."
              steps={[
                { title: 'Identify Discrepancy', description: 'Physical count differs from system quantity. Note variance amount and direction.' },
                { title: 'Investigate Root Cause', description: 'Check recent transactions, look for missed receipts or shipments, verify counting method.', notes: 'Common causes: missed scrap entry, shipping error, data entry mistake.' },
                { title: 'Document Reason', description: 'Select adjustment reason code: Cycle Count, Scrap, Damage, Found, Lost, Other.' },
                { title: 'Supervisor Approval', description: 'Adjustments over $100 or 10% of value require supervisor sign-off.', warning: 'Never adjust without documented justification.' },
                { title: 'Post Adjustment', description: 'Enter adjustment in Inventory > Adjust. Include lot number if applicable.' },
                { title: 'Review Report', description: 'Adjustment creates audit trail record. Finance reviews monthly.' },
              ]}
              qualityChecks={[
                'Reason code accurately reflects cause',
                'Supervisor approved (if required)',
                'Correct lot selected for adjustments',
                'Audit trail complete',
              ]}
            />

            <SopSection
              id="inv-cycle"
              title="SOP-INV-003: Cycle Counting"
              purpose="Maintain inventory accuracy through regular counting procedures."
              scope="All inventory items on scheduled rotation."
              steps={[
                { title: 'Generate Count List', description: 'System creates daily count list based on ABC classification. A items weekly, B monthly, C quarterly.' },
                { title: 'Print Count Sheets', description: 'Generate count sheets showing bin locations but hiding system quantities.' },
                { title: 'Physical Count', description: 'Counter visits each bin, counts items, records on sheet. Two-person count for high-value items.' },
                { title: 'Enter Counts', description: 'Input physical counts into system. System calculates variance.' },
                { title: 'Review Variances', description: 'Investigate any variance > 2%. Recount if needed.' },
                { title: 'Post Adjustments', description: 'Approve count results. System posts adjustments automatically.' },
                { title: 'Analyze Trends', description: 'Review accuracy metrics monthly. Address systemic issues.' },
              ]}
              qualityChecks={[
                'All items on list counted',
                'Variances investigated',
                'Blind counts (no system qty visible)',
                'Accuracy target: 98%+',
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">API Reference</h3>
              <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto">
                <div className="space-y-2">
                  <p className="text-green-400"># Get current stock levels</p>
                  <p>GET /api/v1/inventory</p>
                  <p className="text-green-400 mt-4"># Adjust inventory</p>
                  <p>POST /api/v1/inventory/adjust</p>
                  <p className="text-gray-400">{"{"}</p>
                  <p className="text-gray-400 ml-4">"product_id": 123,</p>
                  <p className="text-gray-400 ml-4">"quantity_change": -5,</p>
                  <p className="text-gray-400 ml-4">"reason": "scrap",</p>
                  <p className="text-gray-400 ml-4">"lot_number": "PLA-BLK-20241201"</p>
                  <p className="text-gray-400">{"}"}</p>
                  <p className="text-green-400 mt-4"># Get low stock alerts</p>
                  <p>GET /api/v1/inventory/alerts</p>
                </div>
              </div>
            </div>
          </div>
        );

      case 'sales':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Sales Order Management</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">Sales Orders capture customer demand from multiple channels. FilaOps supports retail orders (Squarespace sync), custom quotes (portal), and wholesale (B2B). Orders flow through a defined status workflow from draft to shipped.</p>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Order Status Flow</h3>
              <div className="flex flex-wrap items-center justify-center gap-2 p-4 bg-gray-50 rounded">
                {[
                  { status: 'Draft', color: 'bg-gray-500' },
                  { status: 'Confirmed', color: 'bg-blue-500' },
                  { status: 'In Production', color: 'bg-amber-500' },
                  { status: 'Ready', color: 'bg-green-500' },
                  { status: 'Shipped', color: 'bg-purple-500' },
                  { status: 'Delivered', color: 'bg-emerald-500' },
                ].map((step, idx) => (
                  <React.Fragment key={idx}>
                    <div className={`px-3 py-2 ${step.color} text-white rounded text-sm font-medium`}>
                      {step.status}
                    </div>
                    {idx < 5 && <ChevronRight className="w-5 h-5 text-gray-400" />}
                  </React.Fragment>
                ))}
              </div>
            </div>

            <SopSection
              id="so-create"
              title="SOP-SO-001: Creating Sales Orders"
              purpose="Standardize manual order entry from all sales channels."
              scope="Orders from phone, email, or manual portal entry."
              steps={[
                { title: 'Select Customer', description: 'Search existing customer or create new. Verify shipping address and contact.' },
                { title: 'Add Line Items', description: 'Search products by SKU or name. Enter quantity for each item.' },
                { title: 'Apply Pricing', description: 'System pulls price from product or customer-specific price list. Override if needed with approval.', warning: 'Price overrides below margin threshold require manager approval.' },
                { title: 'Set Shipping Method', description: 'Select carrier/service level. System calculates estimated shipping cost.' },
                { title: 'Add Order Notes', description: 'Include special instructions, gift messages, or delivery requirements.' },
                { title: 'Review Totals', description: 'Verify subtotal, tax, shipping, and grand total before confirming.' },
                { title: 'Confirm Order', description: 'Change status from Draft to Confirmed. System allocates inventory and triggers production.' },
              ]}
              qualityChecks={[
                'Customer information accurate',
                'All items have valid SKUs',
                'Pricing matches agreements',
                'Shipping address validated',
              ]}
            />

            <SopSection
              id="so-change"
              title="SOP-SO-002: Order Changes and Cancellations"
              purpose="Handle modifications to confirmed orders properly."
              scope="Any changes to orders after confirmation."
              steps={[
                { title: 'Assess Change Timing', description: 'Check production status. Changes easier before production starts.', notes: 'Orders in "Ready" or "Shipped" cannot be modified.' },
                { title: 'Document Request', description: 'Note customer request, date, and reason for change.' },
                { title: 'Quantity Changes', description: 'Increase: check inventory availability. Decrease: release allocated inventory.' },
                { title: 'Item Changes', description: 'Remove old line (releases inventory), add new line (allocates inventory).' },
                { title: 'Address Changes', description: 'Update shipping address. Regenerate shipping quote if carrier/zone changes.' },
                { title: 'Cancellation', description: 'Set order to Cancelled. All inventory allocations released. Production orders cancelled.', warning: 'Partial production may require scrap or rework decision.' },
                { title: 'Notify Customer', description: 'Confirm changes via email. Update expected ship date if affected.' },
              ]}
              qualityChecks={[
                'Change documented with reason',
                'Inventory properly released/allocated',
                'Production notified of changes',
                'Customer confirmation sent',
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Order Channels</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 border rounded">
                  <h5 className="font-semibold text-gray-800 mb-2">🛒 Retail (Squarespace)</h5>
                  <p className="text-sm text-gray-600 mb-2">Consumer orders from website automatically sync to FilaOps.</p>
                  <span className="text-xs px-2 py-1 bg-amber-100 text-amber-800 rounded">Coming Soon</span>
                </div>
                <div className="p-4 border rounded">
                  <h5 className="font-semibold text-gray-800 mb-2">📋 Custom Quotes</h5>
                  <p className="text-sm text-gray-600 mb-2">Portal quotes convert to orders when approved and paid.</p>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">Pro Feature</span>
                </div>
                <div className="p-4 border rounded">
                  <h5 className="font-semibold text-gray-800 mb-2">🏢 B2B Wholesale</h5>
                  <p className="text-sm text-gray-600 mb-2">Partner portal for volume orders with net terms.</p>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">Pro Feature</span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'production':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Production Order Management</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">Production Orders drive manufacturing execution. Each order specifies what to make, quantities, materials to consume, and the sequence of operations. Work centers track machine capacity and utilization.</p>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Production Order Status Flow</h3>
              <div className="flex flex-wrap items-center justify-center gap-2 p-4 bg-gray-50 rounded">
                {[
                  { status: 'Planned', color: 'bg-gray-500' },
                  { status: 'Released', color: 'bg-blue-500' },
                  { status: 'In Progress', color: 'bg-amber-500' },
                  { status: 'QC', color: 'bg-purple-500' },
                  { status: 'Complete', color: 'bg-green-500' },
                ].map((step, idx) => (
                  <React.Fragment key={idx}>
                    <div className={`px-3 py-2 ${step.color} text-white rounded text-sm font-medium`}>
                      {step.status}
                    </div>
                    {idx < 4 && <ChevronRight className="w-5 h-5 text-gray-400" />}
                  </React.Fragment>
                ))}
              </div>
            </div>

            <SopSection
              id="po-create"
              title="SOP-PO-001: Creating Production Orders"
              purpose="Generate manufacturing orders from sales demand or stock replenishment."
              scope="All production for manufactured products."
              steps={[
                { title: 'Identify Demand Source', description: 'Sales order (make-to-order) or MRP suggestion (make-to-stock). Link to source document.' },
                { title: 'Select Product & BOM', description: 'Choose finished good SKU. System loads active BOM revision automatically.' },
                { title: 'Set Quantity', description: 'Enter production quantity. System calculates material requirements.', notes: 'Consider batch sizes for efficient printer utilization.' },
                { title: 'Review Material Availability', description: 'System shows component availability. Flag shortages for procurement.' },
                { title: 'Assign Work Center', description: 'Select printer pool or specific machine. System checks capacity.' },
                { title: 'Set Due Date', description: 'Based on sales order ship date, work backward for production deadline.' },
                { title: 'Save as Planned', description: 'Order created in Planned status. Not yet visible to production floor.' },
              ]}
              qualityChecks={[
                'Correct BOM revision selected',
                'Material availability confirmed',
                'Due date achievable with capacity',
                'Linked to demand source',
              ]}
            />

            <SopSection
              id="po-execute"
              title="SOP-PO-002: Production Execution"
              purpose="Guide operators through the manufacturing process with proper documentation."
              scope="All production floor activities."
              steps={[
                { title: 'View Queue', description: 'Operator sees released orders in work center dashboard, sorted by priority/due date.' },
                { title: 'Start Order', description: 'Select order to work. Status changes to In Progress. Start time recorded.' },
                { title: 'Material Staging', description: 'Pull required filament from bin. Scan lot barcode to record consumption.', warning: 'FIFO: always use oldest lot first. System will warn if wrong lot selected.' },
                { title: 'Printer Setup', description: 'Load filament, verify settings, apply bed adhesive. Record printer used.' },
                { title: 'Execute Print', description: 'Start print job. Monitor first layers. Log any failures or restarts.' },
                { title: 'Post-Processing', description: 'Remove supports, clean parts, install hardware per assembly instructions.' },
                { title: 'Record Output', description: 'Enter quantity completed. Report any scrap with reason code.' },
                { title: 'QC Checkpoint', description: 'Perform inspection per product spec. Record results. Pass/Fail decision.' },
                { title: 'Complete Order', description: 'All operations done, QC passed. Mark complete. Finished goods to inventory.' },
              ]}
              qualityChecks={[
                'Correct materials consumed (lot tracked)',
                'Print completed without critical failures',
                'All post-processing completed',
                'QC inspection passed and documented',
                'Output quantity matches order (or scrap recorded)',
              ]}
            />

            <SopSection
              id="po-failure"
              title="SOP-PO-003: Production Failure Handling"
              purpose="Document procedures for handling print failures and scrap."
              scope="Any production that does not meet quality standards."
              steps={[
                { title: 'Identify Failure Type', description: 'Classify: Print failure (adhesion, layer shift), Machine error (filament jam, power loss), Quality reject (dimensions, cosmetics).' },
                { title: 'Stop Production', description: 'Cancel current print if in progress. Do not continue printing defective parts.' },
                { title: 'Document Failure', description: 'Record failure in production order: time, failure mode, suspected cause.', notes: 'Photos helpful for recurring issues analysis.' },
                { title: 'Assess Material Impact', description: 'Calculate filament wasted. Record as scrap consumption against production order.' },
                { title: 'Root Cause Analysis', description: 'For recurring failures, investigate: settings, material quality, machine maintenance.' },
                { title: 'Restart Decision', description: 'Supervisor approves restart. May need new material lot or different machine.' },
                { title: 'Update Order Quantity', description: 'If partial completion, adjust expected output. May need supplemental order.' },
              ]}
              qualityChecks={[
                'Failure fully documented with reason code',
                'Scrap material consumption recorded',
                'Root cause identified (if pattern)',
                'Restart properly authorized',
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Work Center Configuration</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="text-left p-2">Work Center</th>
                      <th className="text-left p-2">Machines</th>
                      <th className="text-right p-2">Capacity (hrs/day)</th>
                      <th className="text-right p-2">Rate ($/hr)</th>
                      <th className="text-left p-2">Capabilities</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b">
                      <td className="p-2 font-medium">WC-BAMBU-X1C</td>
                      <td className="p-2">5× Bambu X1C</td>
                      <td className="p-2 text-right">100</td>
                      <td className="p-2 text-right">$8.50</td>
                      <td className="p-2">Multi-color, AMS, High-speed</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 font-medium">WC-BAMBU-P1S</td>
                      <td className="p-2">8× Bambu P1S</td>
                      <td className="p-2 text-right">160</td>
                      <td className="p-2 text-right">$5.00</td>
                      <td className="p-2">Standard PLA/PETG</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 font-medium">WC-PRUSA-MK4</td>
                      <td className="p-2">4× Prusa MK4</td>
                      <td className="p-2 text-right">80</td>
                      <td className="p-2 text-right">$6.00</td>
                      <td className="p-2">Precision, Flex materials</td>
                    </tr>
                    <tr>
                      <td className="p-2 font-medium">WC-ASSEMBLY</td>
                      <td className="p-2">Manual stations</td>
                      <td className="p-2 text-right">16</td>
                      <td className="p-2 text-right">$25.00</td>
                      <td className="p-2">Heat-set inserts, Assembly</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      case 'mrp':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Material Requirements Planning (MRP)</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">MRP calculates material and production needs based on demand forecasts, safety stock policies, and lead times. It generates planned production orders and purchase requisitions to ensure materials are available when needed.</p>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">MRP Calculation Logic</h3>
              <div className="bg-gray-50 p-4 rounded font-mono text-sm">
                <pre>{`Net Requirements = 
    Gross Requirements (Demand)
  - On-Hand Inventory
  - Scheduled Receipts (Open POs)
  + Safety Stock
  
If Net Requirements > 0:
  → Generate Planned Order
  → Offset by Lead Time
  → Explode BOM for component demand`}</pre>
              </div>
            </div>

            <SopSection
              id="mrp-run"
              title="SOP-MRP-001: Running MRP"
              purpose="Generate material and production plans based on current demand and inventory."
              scope="All plannable items (manufactured and purchased)."
              steps={[
                { title: 'Review Demand Inputs', description: 'Confirm sales orders, forecast, and safety stock levels are current.' },
                { title: 'Set Planning Horizon', description: 'Define date range for planning. Typically 4-8 weeks for 3D printing operations.' },
                { title: 'Run MRP Calculation', description: 'System processes all items, calculates net requirements, generates suggestions.' },
                { title: 'Review Exceptions', description: 'Address exception messages: overdue orders, insufficient capacity, missing BOMs.', warning: 'Do not ignore exceptions. They indicate planning problems.' },
                { title: 'Evaluate Suggestions', description: 'Review planned production orders and purchase requisitions. Verify quantities reasonable.' },
                { title: 'Firm Planned Orders', description: 'Convert approved suggestions to firm production orders or purchase orders.' },
                { title: 'Communicate Plan', description: 'Share production schedule with floor. Alert purchasing to upcoming needs.' },
              ]}
              qualityChecks={[
                'All exceptions addressed',
                'Lead times realistic',
                'Capacity available for planned production',
                'Critical materials have coverage',
              ]}
            />

            <SopSection
              id="mrp-forecast"
              title="SOP-MRP-002: Demand Forecasting"
              purpose="Create forward-looking demand estimates for make-to-stock items."
              scope="Items with regular demand patterns."
              steps={[
                { title: 'Analyze History', description: 'Review 6-12 months of sales data. Identify trends and seasonality.' },
                { title: 'Calculate Baseline', description: 'Average demand with trend adjustment. Use moving average or exponential smoothing.' },
                { title: 'Apply Seasonality', description: 'Adjust for known seasonal patterns (holiday peaks, summer slowdowns).' },
                { title: 'Factor Promotions', description: 'Add lift for planned marketing campaigns or sales events.' },
                { title: 'Enter Forecast', description: 'Input monthly forecast quantities by SKU into planning system.' },
                { title: 'Review Accuracy', description: 'Compare prior forecasts to actual. Refine method if forecast error > 20%.' },
              ]}
              qualityChecks={[
                'Historical data reviewed',
                'Seasonal factors considered',
                'Forecast covers planning horizon',
                'Prior accuracy acceptable',
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">MRP Output Example</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="text-left p-2">Item</th>
                      <th className="text-left p-2">Type</th>
                      <th className="text-right p-2">Gross Req</th>
                      <th className="text-right p-2">On Hand</th>
                      <th className="text-right p-2">Safety Stock</th>
                      <th className="text-right p-2">Net Req</th>
                      <th className="text-left p-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b bg-green-50">
                      <td className="p-2">FG-WIDGET-001</td>
                      <td className="p-2">Manufactured</td>
                      <td className="p-2 text-right">50</td>
                      <td className="p-2 text-right">12</td>
                      <td className="p-2 text-right">10</td>
                      <td className="p-2 text-right text-red-600 font-medium">48</td>
                      <td className="p-2">→ Plan Production Order</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 pl-4">↳ FIL-PLA-BLK</td>
                      <td className="p-2">Raw Material</td>
                      <td className="p-2 text-right">2,160g</td>
                      <td className="p-2 text-right">3,500g</td>
                      <td className="p-2 text-right">1,000g</td>
                      <td className="p-2 text-right text-green-600">0</td>
                      <td className="p-2">OK - Stock available</td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2 pl-4">↳ HW-M3-8MM</td>
                      <td className="p-2">Purchased</td>
                      <td className="p-2 text-right">192</td>
                      <td className="p-2 text-right">45</td>
                      <td className="p-2 text-right">100</td>
                      <td className="p-2 text-right text-red-600 font-medium">247</td>
                      <td className="p-2">→ Purchase Requisition</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      case 'traceability':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Traceability & Compliance</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">Traceability enables forward and backward tracking through the supply chain. For regulated industries (medical devices, aerospace), this supports recall capability, root cause analysis, and compliance documentation.</p>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Traceability Elements</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 border rounded bg-amber-50">
                  <h5 className="font-semibold text-amber-800 mb-2">Lot Numbers</h5>
                  <p className="text-sm text-amber-700 mb-2">Track raw materials (filament) by batch. Enables identifying all finished goods made from a specific material lot.</p>
                  <p className="text-xs text-amber-600">Format: [Material]-[Color]-[YYYYMMDD]</p>
                  <p className="text-xs text-amber-600">Example: PLA-BLK-20241201</p>
                </div>
                <div className="p-4 border rounded bg-purple-50">
                  <h5 className="font-semibold text-purple-800 mb-2">Serial Numbers</h5>
                  <p className="text-sm text-purple-700 mb-2">Unique identifier for each finished unit. Enables tracking individual item history through customer.</p>
                  <p className="text-xs text-purple-600">Format: [Product]-[YYYYMM]-[Sequence]</p>
                  <p className="text-xs text-purple-600">Example: WIDGET-202412-0001</p>
                </div>
              </div>
            </div>

            <SopSection
              id="trace-forward"
              title="SOP-TRACE-001: Forward Traceability (Lot to Customer)"
              purpose="Identify all finished goods and customers affected by a material lot."
              scope="Material recall scenarios, quality investigations."
              steps={[
                { title: 'Identify Problem Lot', description: 'Record lot number of suspect material. Example: supplier notification of contamination.' },
                { title: 'Query Forward Trace', description: 'Use API: GET /api/v1/admin/traceability/recall/forward/{lot_number}' },
                { title: 'Review Affected Items', description: 'System returns list of production orders and finished good serial numbers using that lot.' },
                { title: 'Identify Customers', description: 'Cross-reference serial numbers to sales orders and shipping records.' },
                { title: 'Assess Impact', description: 'Determine scope: items in inventory, in-transit, delivered to customers.' },
                { title: 'Execute Recall Plan', description: 'Contact affected customers, quarantine in-stock inventory, document actions taken.', warning: 'For medical devices, follow FDA recall procedures and report as required.' },
                { title: 'Document Resolution', description: 'Record all actions, customer communications, and final disposition.' },
              ]}
              qualityChecks={[
                'All affected serial numbers identified',
                'Customer notification documented',
                'Quarantine properly executed',
                'Regulatory reporting complete (if required)',
              ]}
            />

            <SopSection
              id="trace-backward"
              title="SOP-TRACE-002: Backward Traceability (Serial to Materials)"
              purpose="Determine all materials and processes used to make a specific unit."
              scope="Customer complaints, warranty claims, quality investigations."
              steps={[
                { title: 'Obtain Serial Number', description: 'From customer complaint, warranty claim, or internal quality issue.' },
                { title: 'Query Backward Trace', description: 'Use API: GET /api/v1/admin/traceability/recall/backward/{serial_number}' },
                { title: 'Review Production Record', description: 'System returns production order, date, operator, machine used.' },
                { title: 'Identify Material Lots', description: 'View all lot numbers consumed in production of that unit.' },
                { title: 'Correlate Issues', description: 'Compare to other units from same lot. Look for patterns.' },
                { title: 'Root Cause Analysis', description: 'Use complete history to investigate: material issue, process issue, or handling.' },
                { title: 'Corrective Action', description: 'Document findings and preventive measures.' },
              ]}
              qualityChecks={[
                'Complete production history retrieved',
                'All component lots identified',
                'Root cause documented',
                'Corrective action defined',
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Compliance Standards Supported</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 border rounded">
                  <h5 className="font-semibold text-gray-800 mb-2">ISO 13485</h5>
                  <p className="text-sm text-gray-600">Medical device quality management. Requires complete traceability from raw material to patient.</p>
                </div>
                <div className="p-4 border rounded">
                  <h5 className="font-semibold text-gray-800 mb-2">FDA 21 CFR 820</h5>
                  <p className="text-sm text-gray-600">US medical device regulations. Device History Record (DHR) requirements.</p>
                </div>
                <div className="p-4 border rounded">
                  <h5 className="font-semibold text-gray-800 mb-2">AS9100</h5>
                  <p className="text-sm text-gray-600">Aerospace quality management. Configuration management and traceability.</p>
                </div>
              </div>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">API Reference</h3>
              <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto">
                <div className="space-y-2">
                  <p className="text-green-400"># List material lots</p>
                  <p>GET /api/v1/admin/traceability/lots</p>
                  <p className="text-green-400 mt-4"># List serial numbers</p>
                  <p>GET /api/v1/admin/traceability/serials</p>
                  <p className="text-green-400 mt-4"># Forward trace (lot → finished goods)</p>
                  <p>GET /api/v1/admin/traceability/recall/forward/{"{lot_number}"}</p>
                  <p className="text-green-400 mt-4"># Backward trace (serial → materials)</p>
                  <p>GET /api/v1/admin/traceability/recall/backward/{"{serial_number}"}</p>
                </div>
              </div>
            </div>
          </div>
        );

      case 'integrations':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">System Integrations</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">FilaOps integrates with external services for payments, shipping, accounting, and e-commerce. Proper configuration ensures smooth data flow between systems.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 border rounded">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-purple-600 rounded flex items-center justify-center text-white font-bold">S</div>
                  <div>
                    <h4 className="font-semibold">Stripe</h4>
                    <span className="text-xs px-2 py-0.5 bg-green-100 text-green-800 rounded">Active</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-2">Payment processing for customer orders and invoices.</p>
                <p className="text-xs text-gray-500">Config: STRIPE_SECRET_KEY in .env</p>
              </div>

              <div className="p-4 border rounded">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-blue-600 rounded flex items-center justify-center text-white font-bold">E</div>
                  <div>
                    <h4 className="font-semibold">EasyPost</h4>
                    <span className="text-xs px-2 py-0.5 bg-green-100 text-green-800 rounded">Active</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-2">Multi-carrier shipping rates and label generation.</p>
                <p className="text-xs text-gray-500">Config: EASYPOST_API_KEY in .env</p>
              </div>

              <div className="p-4 border rounded">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-black rounded flex items-center justify-center text-white font-bold">□</div>
                  <div>
                    <h4 className="font-semibold">Squarespace</h4>
                    <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-800 rounded">Coming Soon</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-2">Sync retail orders from website to FilaOps.</p>
                <p className="text-xs text-gray-500">Two-way sync: orders, inventory, products</p>
              </div>

              <div className="p-4 border rounded">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-green-600 rounded flex items-center justify-center text-white font-bold">Q</div>
                  <div>
                    <h4 className="font-semibold">QuickBooks</h4>
                    <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-800 rounded">Coming Soon</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-2">Accounting integration for invoices and payments.</p>
                <p className="text-xs text-gray-500">Sync: invoices, payments, customers</p>
              </div>
            </div>

            <SopSection
              id="int-stripe"
              title="SOP-INT-001: Stripe Payment Processing"
              purpose="Configure and manage payment collection through Stripe."
              scope="All customer payments via credit card or ACH."
              steps={[
                { title: 'Obtain API Keys', description: 'From Stripe Dashboard > Developers > API Keys. Use test keys for development.' },
                { title: 'Configure Environment', description: 'Set STRIPE_SECRET_KEY in .env file. Never commit keys to version control.', warning: 'Protect secret keys. Exposure requires immediate key rotation.' },
                { title: 'Enable Payment Methods', description: 'In Stripe Dashboard, enable desired methods: cards, ACH, etc.' },
                { title: 'Test Integration', description: 'Use test card numbers to verify payment flow. Confirm webhook delivery.' },
                { title: 'Go Live', description: 'Switch to live API keys. Verify first real transaction.' },
              ]}
            />

            <SopSection
              id="int-easypost"
              title="SOP-INT-002: EasyPost Shipping Setup"
              purpose="Configure multi-carrier shipping rate shopping and label generation."
              scope="All outbound shipments."
              steps={[
                { title: 'Create EasyPost Account', description: 'Sign up at easypost.com. Complete carrier agreements for desired carriers.' },
                { title: 'Add Carrier Accounts', description: 'Connect UPS, FedEx, USPS, DHL accounts to EasyPost.' },
                { title: 'Configure API Key', description: 'Set EASYPOST_API_KEY in .env. Test mode available for development.' },
                { title: 'Set Shipping Preferences', description: 'Define default package dimensions, origin address, carrier preferences.' },
                { title: 'Test Label Generation', description: 'Create test shipment, verify rates, generate void label.' },
                { title: 'Production Use', description: 'Rate shop for each shipment. Generate labels. Track with webhook updates.' },
              ]}
            />
          </div>
        );

      case 'admin':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">System Administration</h2>
            
            <div className="p-4 border rounded-lg bg-blue-50">
              <h3 className="font-bold text-blue-800 mb-2">Module Overview</h3>
              <p className="text-blue-700 text-sm">Administration covers user management, system configuration, security, and maintenance procedures. Proper administration ensures system reliability and data integrity.</p>
            </div>

            <SopSection
              id="admin-user"
              title="SOP-ADMIN-001: User Management"
              purpose="Control user access and permissions."
              scope="All system users."
              steps={[
                { title: 'Create User Account', description: 'Admin creates account with email. User receives password reset link.' },
                { title: 'Assign Role', description: 'Select appropriate role: Admin, Manager, Operator, Viewer.' },
                { title: 'Set Permissions', description: 'Fine-tune module access if needed. Some roles have preset permissions.' },
                { title: 'Activate Account', description: 'User completes password setup. Account becomes active.' },
                { title: 'Review Periodically', description: 'Quarterly review of user access. Disable inactive accounts.' },
                { title: 'Offboarding', description: 'Immediately disable accounts for departing employees.' },
              ]}
            />

            <SopSection
              id="admin-backup"
              title="SOP-ADMIN-002: Database Backup & Recovery"
              purpose="Protect data through regular backups and tested recovery procedures."
              scope="All FilaOps data."
              steps={[
                { title: 'Configure Automated Backups', description: 'SQL Server Agent job for daily full backup, hourly transaction log backup.' },
                { title: 'Verify Backup Success', description: 'Check backup job history daily. Alert on failures.' },
                { title: 'Offsite Storage', description: 'Copy backups to secondary location (cloud storage, offsite server).', warning: 'Local-only backups risk data loss in disaster scenario.' },
                { title: 'Test Recovery', description: 'Monthly restore test to verify backups are usable. Document restore time.' },
                { title: 'Retention Policy', description: 'Keep daily backups 30 days, weekly 90 days, monthly 1 year.' },
              ]}
            />

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">User Roles & Permissions</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="text-left p-2">Permission</th>
                      <th className="text-center p-2">Admin</th>
                      <th className="text-center p-2">Manager</th>
                      <th className="text-center p-2">Operator</th>
                      <th className="text-center p-2">Viewer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { perm: 'View Products', admin: true, manager: true, operator: true, viewer: true },
                      { perm: 'Edit Products', admin: true, manager: true, operator: false, viewer: false },
                      { perm: 'Create Orders', admin: true, manager: true, operator: true, viewer: false },
                      { perm: 'View Inventory', admin: true, manager: true, operator: true, viewer: true },
                      { perm: 'Adjust Inventory', admin: true, manager: true, operator: true, viewer: false },
                      { perm: 'Execute Production', admin: true, manager: true, operator: true, viewer: false },
                      { perm: 'Run MRP', admin: true, manager: true, operator: false, viewer: false },
                      { perm: 'Traceability Queries', admin: true, manager: true, operator: false, viewer: false },
                      { perm: 'User Management', admin: true, manager: false, operator: false, viewer: false },
                      { perm: 'System Config', admin: true, manager: false, operator: false, viewer: false },
                    ].map((row, idx) => (
                      <tr key={idx} className="border-b">
                        <td className="p-2">{row.perm}</td>
                        <td className="p-2 text-center">{row.admin ? '✅' : '—'}</td>
                        <td className="p-2 text-center">{row.manager ? '✅' : '—'}</td>
                        <td className="p-2 text-center">{row.operator ? '✅' : '—'}</td>
                        <td className="p-2 text-center">{row.viewer ? '✅' : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="p-4 border rounded-lg">
              <h3 className="font-bold text-lg mb-4">Environment Configuration</h3>
              <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto">
                <pre>{`# Database Connection
DB_HOST=localhost\\SQLEXPRESS
DB_NAME=FilaOps
DB_TRUSTED_CONNECTION=true

# Security
SECRET_KEY=your-secure-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Integrations
STRIPE_SECRET_KEY=sk_live_...
EASYPOST_API_KEY=EZTK...

# Application
LOG_LEVEL=INFO
ENVIRONMENT=production`}</pre>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r flex-shrink-0 overflow-y-auto">
        <div className="p-4 border-b">
          <h1 className="font-bold text-lg text-gray-800">FilaOps</h1>
          <p className="text-sm text-gray-500">SOPs & User Guide</p>
        </div>
        <nav className="p-2">
          {sections.map(section => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
                activeSection === section.id
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <section.icon className="w-4 h-4" />
              {section.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default FilaOpsDocumentation;
