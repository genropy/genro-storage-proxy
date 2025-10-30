"""NiceGUI web interface for genro-storage-proxy admin."""

from typing import Dict, Any
import httpx
from nicegui import ui
from genro_storage_proxy.persistence import Persistence
from genro_storage import StorageManager


class AdminUI:
    """Admin UI for managing storage volumes."""

    def __init__(self, persistence: Persistence, storage_manager: StorageManager):
        self.persistence = persistence
        self.storage_manager = storage_manager
        self.volumes_container = None
        self.file_browser_container = None
        self.selected_volume = None
        self.tree_widget = None

    async def refresh_volumes(self):
        """Refresh the volumes list."""
        if self.volumes_container:
            self.volumes_container.clear()
            with self.volumes_container:
                volumes = await self.persistence.list_volumes()
                if not volumes:
                    ui.label("No volumes configured").classes("text-gray-500 italic")
                else:
                    for vol in volumes:
                        await self.render_volume_card(vol)

    async def render_volume_card(self, volume: Dict[str, Any]):
        """Render a single volume card."""
        is_selected = self.selected_volume == volume["name"]
        card_class = "w-full mb-2 cursor-pointer"
        if is_selected:
            card_class += " border-2 border-primary"

        with ui.card().classes(card_class).on("click", lambda v=volume: self.select_volume(v["name"])):
            with ui.row().classes("w-full items-center"):
                with ui.column().classes("flex-grow"):
                    ui.label(volume["name"]).classes("text-lg font-bold")
                    ui.label(f"Backend: {volume['backend']}").classes("text-sm text-gray-600")
                    ui.label(f"Config: {volume['config']}").classes("text-xs text-gray-500")

                ui.button(icon="delete", on_click=lambda v=volume: self.confirm_delete_volume(v["name"])).props("flat color=negative")

    def confirm_delete_volume(self, volume_name: str):
        """Show confirmation dialog for volume deletion."""
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete volume '{volume_name}'?").classes("text-lg")
            ui.label("This action cannot be undone.").classes("text-sm text-gray-600")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Delete", on_click=lambda: self.delete_volume(volume_name, dialog)).props("color=negative")

        dialog.open()

    async def delete_volume(self, volume_name: str, dialog):
        """Delete a volume."""
        try:
            deleted = await self.persistence.delete_volume(volume_name)
            if deleted:
                ui.notify(f"Volume '{volume_name}' deleted successfully", type="positive")
                await self.refresh_volumes()
            else:
                ui.notify(f"Volume '{volume_name}' not found", type="negative")
        except Exception as e:
            ui.notify(f"Error deleting volume: {str(e)}", type="negative")
        finally:
            dialog.close()

    def show_add_volume_dialog(self):
        """Show dialog to select backend type."""
        backend_type = {"value": "local"}  # Default selection

        with ui.dialog() as dialog:
            with ui.card() as card:
                content_container = ui.column().classes("w-full")

                with content_container:
                    ui.label("Create New Volume - Select Backend").classes("text-lg font-bold mb-4")

                    ui.select(
                        label="Storage Backend",
                        options=["local", "s3", "gcs", "azure", "http", "memory", "smb", "sftp", "zip", "tar", "git", "github", "webdav", "libarchive", "base64"],
                        value="local"
                    ).bind_value(backend_type, "value").classes("w-full")

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):
                        ui.button("Cancel", on_click=dialog.close)
                        ui.button("Next", on_click=lambda: self.show_backend_form(backend_type["value"], dialog, content_container)).props("color=primary")

        dialog.open()

    def show_backend_form(self, backend: str, dialog, content_container):
        """Show backend-specific form dialog."""
        # Clear current content
        content_container.clear()

        # Form data storage
        form_data = {}

        with content_container:
            ui.label(f"Create {backend.upper()} Volume").classes("text-lg font-bold mb-4")

            # Common field: name
            form_data["name"] = ui.input(label="Volume Name", placeholder="e.g., uploads").classes("w-full")

            # Backend-specific fields
            if backend == "s3":
                form_data["bucket"] = ui.input(label="Bucket Name", placeholder="e.g., my-bucket").classes("w-full")
                form_data["region"] = ui.input(label="Region", placeholder="e.g., us-east-1").classes("w-full")
                form_data["endpoint_url"] = ui.input(label="Endpoint URL (optional)", placeholder="For S3-compatible services").classes("w-full")

            elif backend == "gcs":
                form_data["bucket"] = ui.input(label="Bucket Name", placeholder="e.g., my-bucket").classes("w-full")
                form_data["project"] = ui.input(label="Project ID", placeholder="e.g., my-project").classes("w-full")

            elif backend == "local":
                form_data["path"] = ui.input(label="Directory Path", placeholder="e.g., /data/uploads").classes("w-full")

            elif backend == "azure":
                form_data["container"] = ui.input(label="Container Name", placeholder="e.g., my-container").classes("w-full")
                form_data["account_name"] = ui.input(label="Account Name", placeholder="Storage account name").classes("w-full")
                form_data["account_key"] = ui.input(label="Account Key (optional)", placeholder="For authentication", password=True).classes("w-full")

            elif backend == "http":
                form_data["base_url"] = ui.input(label="Base URL", placeholder="e.g., https://cdn.example.com").classes("w-full")

            elif backend == "memory":
                ui.label("Memory storage doesn't require configuration").classes("text-sm text-gray-600")

            elif backend == "smb":
                form_data["host"] = ui.input(label="Host", placeholder="e.g., server.example.com").classes("w-full")
                form_data["share"] = ui.input(label="Share Name", placeholder="e.g., shared").classes("w-full")
                form_data["username"] = ui.input(label="Username (optional)", placeholder="For authentication").classes("w-full")
                form_data["password"] = ui.input(label="Password (optional)", placeholder="For authentication", password=True).classes("w-full")
                form_data["domain"] = ui.input(label="Domain (optional)", placeholder="Windows domain").classes("w-full")
                form_data["port"] = ui.input(label="Port (optional)", placeholder="Default: 445").classes("w-full")

            elif backend == "sftp":
                form_data["host"] = ui.input(label="Host", placeholder="e.g., sftp.example.com").classes("w-full")
                form_data["username"] = ui.input(label="Username", placeholder="SSH username").classes("w-full")
                form_data["password"] = ui.input(label="Password (optional)", placeholder="For password auth", password=True).classes("w-full")
                form_data["port"] = ui.input(label="Port (optional)", placeholder="Default: 22").classes("w-full")
                form_data["key_filename"] = ui.input(label="SSH Key Path (optional)", placeholder="e.g., /home/user/.ssh/id_rsa").classes("w-full")
                form_data["passphrase"] = ui.input(label="Key Passphrase (optional)", placeholder="For encrypted keys", password=True).classes("w-full")

            elif backend == "zip":
                form_data["file"] = ui.input(label="ZIP File Path", placeholder="e.g., /data/archive.zip").classes("w-full")
                form_data["mode"] = ui.input(label="Mode (optional)", placeholder="r (read) or w (write)").classes("w-full")

            elif backend == "tar":
                form_data["file"] = ui.input(label="TAR File Path", placeholder="e.g., /data/archive.tar.gz").classes("w-full")
                form_data["compression"] = ui.input(label="Compression (optional)", placeholder="e.g., gz, bz2, xz").classes("w-full")

            elif backend == "git":
                form_data["path"] = ui.input(label="Git Repository Path", placeholder="e.g., /path/to/repo").classes("w-full")
                form_data["ref"] = ui.input(label="Branch/Tag/Commit (optional)", placeholder="e.g., main, v1.0.0").classes("w-full")

            elif backend == "github":
                form_data["org"] = ui.input(label="Organization/Username", placeholder="e.g., genropy").classes("w-full")
                form_data["repo"] = ui.input(label="Repository Name", placeholder="e.g., genro-storage").classes("w-full")
                form_data["sha"] = ui.input(label="Branch/Tag/SHA (optional)", placeholder="e.g., main").classes("w-full")
                form_data["username"] = ui.input(label="GitHub Username (optional)", placeholder="For private repos").classes("w-full")
                form_data["token"] = ui.input(label="Access Token (optional)", placeholder="Personal access token", password=True).classes("w-full")

            elif backend == "webdav":
                form_data["url"] = ui.input(label="WebDAV URL", placeholder="e.g., https://nextcloud.example.com/remote.php/dav/files/user/").classes("w-full")
                form_data["username"] = ui.input(label="Username (optional)", placeholder="For authentication").classes("w-full")
                form_data["password"] = ui.input(label="Password (optional)", placeholder="For authentication", password=True).classes("w-full")
                form_data["token"] = ui.input(label="Token (optional)", placeholder="Bearer token", password=True).classes("w-full")

            elif backend == "libarchive":
                form_data["file"] = ui.input(label="Archive File Path", placeholder="e.g., /data/archive.7z").classes("w-full")
                ui.label("Supports: 7z, rar, iso, cab, and many more formats").classes("text-xs text-gray-500")

            elif backend == "base64":
                ui.label("Base64 backend doesn't require configuration").classes("text-sm text-gray-600")
                ui.label("Used for inline data URIs (data:...)").classes("text-xs text-gray-500")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Back", on_click=lambda: self.back_to_backend_selection(dialog, content_container))
                ui.button("Create", on_click=lambda: self.create_volume(backend, form_data, dialog)).props("color=primary")

    def back_to_backend_selection(self, dialog, content_container):
        """Go back to backend selection dialog."""
        # Clear current content
        content_container.clear()

        # Rebuild backend selection form
        backend_type = {"value": "local"}

        with content_container:
            ui.label("Create New Volume - Select Backend").classes("text-lg font-bold mb-4")

            ui.select(
                label="Storage Backend",
                options=["local", "s3", "gcs", "azure", "http", "memory", "smb", "sftp", "zip", "tar", "git", "github", "webdav", "libarchive", "base64"],
                value="local"
            ).bind_value(backend_type, "value").classes("w-full")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Next", on_click=lambda: self.show_backend_form(backend_type["value"], dialog, content_container)).props("color=primary")

    async def create_volume(self, backend: str, form_data: Dict, dialog):
        """Create a new volume."""
        try:
            # Extract form values
            name = form_data["name"].value
            if not name:
                ui.notify("Volume name is required", type="warning")
                return

            # Build config based on backend
            config = {}

            if backend == "s3":
                bucket = form_data["bucket"].value
                region = form_data["region"].value
                if not bucket or not region:
                    ui.notify("Bucket and region are required for S3", type="warning")
                    return
                config["bucket"] = bucket
                config["region"] = region
                if form_data["endpoint_url"].value:
                    config["endpoint_url"] = form_data["endpoint_url"].value

            elif backend == "gcs":
                bucket = form_data["bucket"].value
                project = form_data["project"].value
                if not bucket or not project:
                    ui.notify("Bucket and project are required for GCS", type="warning")
                    return
                config["bucket"] = bucket
                config["project"] = project

            elif backend == "local":
                path = form_data["path"].value
                if not path:
                    ui.notify("Path is required for local storage", type="warning")
                    return
                config["path"] = path

            elif backend == "azure":
                container = form_data["container"].value
                account_name = form_data["account_name"].value
                if not container or not account_name:
                    ui.notify("Container and account name are required for Azure", type="warning")
                    return
                config["container"] = container
                config["account_name"] = account_name
                if form_data["account_key"].value:
                    config["account_key"] = form_data["account_key"].value

            elif backend == "http":
                base_url = form_data["base_url"].value
                if not base_url:
                    ui.notify("Base URL is required for HTTP storage", type="warning")
                    return
                config["base_url"] = base_url

            elif backend == "memory":
                # Memory storage has no configuration
                pass

            elif backend == "smb":
                host = form_data["host"].value
                share = form_data["share"].value
                if not host or not share:
                    ui.notify("Host and share are required for SMB", type="warning")
                    return
                config["host"] = host
                config["share"] = share
                if form_data["username"].value:
                    config["username"] = form_data["username"].value
                if form_data["password"].value:
                    config["password"] = form_data["password"].value
                if form_data["domain"].value:
                    config["domain"] = form_data["domain"].value
                if form_data["port"].value:
                    config["port"] = int(form_data["port"].value)

            elif backend == "sftp":
                host = form_data["host"].value
                username = form_data["username"].value
                if not host or not username:
                    ui.notify("Host and username are required for SFTP", type="warning")
                    return
                config["host"] = host
                config["username"] = username
                if form_data["password"].value:
                    config["password"] = form_data["password"].value
                if form_data["port"].value:
                    config["port"] = int(form_data["port"].value)
                if form_data["key_filename"].value:
                    config["key_filename"] = form_data["key_filename"].value
                if form_data["passphrase"].value:
                    config["passphrase"] = form_data["passphrase"].value

            elif backend == "zip":
                file = form_data["file"].value
                if not file:
                    ui.notify("File path is required for ZIP", type="warning")
                    return
                config["file"] = file
                if form_data["mode"].value:
                    config["mode"] = form_data["mode"].value

            elif backend == "tar":
                file = form_data["file"].value
                if not file:
                    ui.notify("File path is required for TAR", type="warning")
                    return
                config["file"] = file
                if form_data["compression"].value:
                    config["compression"] = form_data["compression"].value

            elif backend == "git":
                path = form_data["path"].value
                if not path:
                    ui.notify("Repository path is required for Git", type="warning")
                    return
                config["path"] = path
                if form_data["ref"].value:
                    config["ref"] = form_data["ref"].value

            elif backend == "github":
                org = form_data["org"].value
                repo = form_data["repo"].value
                if not org or not repo:
                    ui.notify("Organization and repository are required for GitHub", type="warning")
                    return
                config["org"] = org
                config["repo"] = repo
                if form_data["sha"].value:
                    config["sha"] = form_data["sha"].value
                if form_data["username"].value:
                    config["username"] = form_data["username"].value
                if form_data["token"].value:
                    config["token"] = form_data["token"].value

            elif backend == "webdav":
                url = form_data["url"].value
                if not url:
                    ui.notify("URL is required for WebDAV", type="warning")
                    return
                config["url"] = url
                if form_data["username"].value:
                    config["username"] = form_data["username"].value
                if form_data["password"].value:
                    config["password"] = form_data["password"].value
                if form_data["token"].value:
                    config["token"] = form_data["token"].value

            elif backend == "libarchive":
                file = form_data["file"].value
                if not file:
                    ui.notify("File path is required for LibArchive", type="warning")
                    return
                config["file"] = file

            elif backend == "base64":
                # Base64 backend has no configuration
                pass

            # Create volume
            await self.persistence.add_volume({
                "name": name,
                "backend": backend,
                "config": config
            })

            # Register in storage manager using configure()
            self.storage_manager.configure([{
                "name": name,
                "type": backend,
                **config
            }])

            ui.notify(f"Volume '{name}' created successfully", type="positive")
            await self.refresh_volumes()
            dialog.close()

        except Exception as e:
            ui.notify(f"Error creating volume: {str(e)}", type="negative")

    async def select_volume(self, volume_name: str):
        """Select a volume and show file browser."""
        self.selected_volume = volume_name
        await self.refresh_volumes()
        await self.load_file_browser()

    async def fetch_children(self, volume_name: str, path: str = ""):
        """Fetch children nodes from API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:8080/admin/volumes/{volume_name}/browse",
                    params={"path": path}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            ui.notify(f"Error loading files: {str(e)}", type="negative")
            return []

    async def on_expand_node(self, e):
        """Handle expansion of tree nodes - load children dynamically."""
        print(f"[DEBUG] on_expand_node called with e={e}, e.value={e.value if hasattr(e, 'value') else 'NO VALUE'}, e.args={e.args if hasattr(e, 'args') else 'NO ARGS'}")

        # e.value contains the node id that was expanded
        node_id = e.value if e.value else None

        if not node_id or not self.selected_volume:
            print(f"[DEBUG] Skipping: node_id={node_id}, selected_volume={self.selected_volume}")
            return

        print(f"[DEBUG] Loading children for node_id={node_id}, volume={self.selected_volume}")

        # Find the node in the tree's _props
        nodes = self.tree_widget._props.get('nodes', [])
        target_node = self._find_node_by_id(nodes, node_id)

        if target_node and target_node.get('lazy', False):
            # Check if children already loaded
            if 'children' not in target_node or not target_node.get('children'):
                # Load children from API
                print(f"[DEBUG] Fetching children from API...")
                children = await self.fetch_children(self.selected_volume, node_id)
                print(f"[DEBUG] Got {len(children)} children")
                target_node['children'] = children
                # Don't remove lazy - keep it for Quasar tree
                self.tree_widget.update()
                print(f"[DEBUG] Tree updated")
        else:
            print(f"[DEBUG] Node not found or not lazy: target_node={target_node}")

    def _find_node_by_id(self, nodes, node_id):
        """Recursively find a node by id in the tree."""
        if not nodes:
            return None
        for node in nodes:
            if node.get('id') == node_id:
                return node
            if 'children' in node and node.get('children'):
                result = self._find_node_by_id(node['children'], node_id)
                if result:
                    return result
        return None

    async def _expand_all_nodes(self, nodes, max_depth=2, current_depth=0):
        """Expand tree nodes recursively up to max_depth."""
        if current_depth >= max_depth:
            return nodes

        expanded_nodes = []
        for node in nodes:
            expanded_node = node.copy()

            # If node has lazy flag and empty children, load them
            if expanded_node.get('lazy') and not expanded_node.get('children'):
                children = await self.fetch_children(self.selected_volume, expanded_node['id'])
                if children:
                    # Recursively expand children
                    expanded_children = await self._expand_all_nodes(children, max_depth, current_depth + 1)
                    expanded_node['children'] = expanded_children

            expanded_nodes.append(expanded_node)

        return expanded_nodes

    async def on_file_select(self, e):
        """Handle file selection in tree."""
        node = e.value
        if not node.get('lazy'):  # It's a file, not a directory
            ui.notify(f"Selected file: {node['label']}", type="info")

    async def load_file_browser(self):
        """Load file browser for selected volume."""
        if not self.selected_volume:
            return

        if self.file_browser_container:
            self.file_browser_container.clear()

            with self.file_browser_container:
                ui.label(f"Files in '{self.selected_volume}'").classes("text-h6 mb-4")

                # Load root nodes
                root_nodes = await self.fetch_children(self.selected_volume, "")

                if root_nodes:
                    # Per ora carichiamo tutto l'albero in una volta
                    # TODO: implementare lazy loading vero
                    expanded_nodes = await self._expand_all_nodes(root_nodes, max_depth=2)
                    self.tree_widget = ui.tree(
                        expanded_nodes,
                        on_select=self.on_file_select
                    ).classes("w-full")
                else:
                    ui.label("No files found or volume is empty").classes("text-gray-500 italic")

    async def render(self):
        """Render the main UI."""
        ui.page_title("Genro Storage Proxy - Admin")

        with ui.header().classes("items-center justify-between"):
            ui.label("Genro Storage Proxy").classes("text-h5")

        with ui.row().classes("w-full h-full"):
            # Left column: Volumes list
            with ui.column().classes("w-1/3 p-4"):
                with ui.row().classes("w-full items-center justify-between mb-4"):
                    ui.label("Storage Volumes").classes("text-h6")
                    ui.button(icon="add", on_click=self.show_add_volume_dialog).props("round color=primary")

                # Volumes container
                self.volumes_container = ui.column().classes("w-full")
                await self.refresh_volumes()

            # Right column: File browser
            with ui.column().classes("w-2/3 p-4 bg-gray-50"):
                self.file_browser_container = ui.column().classes("w-full")
                with self.file_browser_container:
                    ui.label("File Browser").classes("text-h6 text-gray-400")
                    ui.label("Select a volume to browse files").classes("text-sm text-gray-400 italic")


def init_ui(persistence: Persistence, storage_manager: StorageManager):
    """Initialize the NiceGUI interface."""
    admin_ui = AdminUI(persistence, storage_manager)

    @ui.page("/admin/ui")
    async def admin_page():
        await admin_ui.render()
