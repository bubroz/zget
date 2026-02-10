"""
Plex NFO sidecar generation.

Creates .nfo files for videos to ensure Plex/Jellyfin correctly identify social media archival.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from ..db.models import Video


def generate_nfo(video: Video, output_path: Path) -> Path:
    """
    Generate a Plex-compatible .nfo file for a video.

    Args:
        video: Video model containing metadata
        output_path: Destination path for the .nfo file (usually video_path.with_suffix('.nfo'))

    Returns:
        Path to the generated .nfo file
    """
    root = ET.Element("movie")  # Plex "Other Videos" often works best with movie or episodedetails

    title = ET.SubElement(root, "title")
    title.text = video.title

    if video.description:
        plot = ET.SubElement(root, "plot")
        plot.text = video.description

    if video.uploader:
        studio = ET.SubElement(root, "studio")
        studio.text = f"{video.platform.capitalize()} - {video.uploader}"

        # Also add as a tag for easier filtering
        tag = ET.SubElement(root, "tag")
        tag.text = video.uploader

    if video.upload_date:
        year = ET.SubElement(root, "year")
        year.text = str(video.upload_date.year)

        premiered = ET.SubElement(root, "premiered")
        premiered.text = video.upload_date.strftime("%Y-%m-%d")

    if video.duration_seconds:
        runtime = ET.SubElement(root, "runtime")
        runtime.text = str(int(video.duration_seconds // 60))

    # Add source URL as a unique ID
    uniqueid = ET.SubElement(root, "uniqueid", type="zget", default="true")
    uniqueid.text = video.url

    # Add tags
    for t in video.tags:
        tag_element = ET.SubElement(root, "tag")
        tag_element.text = t

    # Helper for pretty printing
    xml_str = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(xml_str)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    return output_path
