"""
Plotting functions of Vi go here. 
"""
import plotly.express as px
import plotly.graph_objects as go
from tqdm.notebook import tqdm
import copy
from typing import Union, List, Dict, Any
from .score import ViScore
from .utils import ViAnalyticsUtils, MeanDict
from ..read import ViReadClient
from ..errors import APIError

class VizMixin(ViScore, ViAnalyticsUtils):
    """
    Visualisation submodule for the library.
    """

    def _scatter_plot_documents(
        self,
        filtered_collection: list,
        dim_reduction_field: str,
        color: str,
        point_label: str,
        title: str=None,
        mode: str='markers',
        marker_size:int = 5
    ):
        """
        Add additional plot to figure and filtered collection and dim reduction field.

        Args:
            filtered_collection:
                A collection or the name of a collection
            dim_reduction_field:
                Dimensionally reduced field.
            color:
                Color of the plot
            point_label:
                Label of the plot
            title:
                Name of the group of documents

        Returns:
            go.Scatter: Scatter plot of centroids.

        """
        return go.Scatter(
            x=[
                self.get_field(dim_reduction_field, x)[0]
                for x in filtered_collection
            ],
            y=[
                self.get_field(dim_reduction_field, x)[1]
                for x in filtered_collection
            ],
            mode=mode,
            marker=dict(size=marker_size, color=color),
            text=[x[point_label] for x in filtered_collection],
            name=title,
        )

    def _scatter_plot_centroids(
        self,
        cluster_centroid_documents: List[Dict],
        dim_reduction_field: str,
        point_label: str,
        line_color="DarkSlateGrey",
        line_width=2,
        size=5,
        color_dict=None,
        mode: str='markers',
        color='orange',
    ):
        """
        Scatterplot the centroids

        Args:
            cluster_centroid_documents:
                The centroids to highlight.
            point_label:
                The label of every point. This should be found in the document.
            dim_reduction_field:
                The dimensionally-reduced vectors.
            line_width:
                The width of the lines.
            line_color:
                THe line color of the centroids
            color_dict:
                What to color the centroid the cluster label/title
            size:
                The size of the markers for the centroid documents
        
        Returns:
            go.Scatter: Scatter plot of the documents
        
        """
        x = [
            self.get_field(dim_reduction_field, x)[0]
            for x in cluster_centroid_documents.values()
        ]
        y = [
            self.get_field(dim_reduction_field, x)[1]
            for x in cluster_centroid_documents.values()
        ]
        titles = [
            self.get_field(point_label, x)
            for x in cluster_centroid_documents.values()
        ]
        return go.Scatter(
            x=x,
            y=y,
            mode=mode,
            marker=dict(
                size=size,
                # color=[color_dict[str(x['_clusters_'][cluster_field]['title'])] for x in cluster_centroids.values()],
                color=color,
                line=dict(width=line_width, color=line_color),
            ),
            text=titles,
            name="centroids",
        )

    def plot_dimensionality_reduced_vectors(
        self,
        collection: Union[str, List[Dict]],
        point_label: str,
        dim_reduction_field: str,
        cluster_field: str=None,
        cluster_label: str=None,
        include_centroids: bool = False,
        color: str=None,
        alias: str = None,
        mode: str='markers',
    ):
        """
        Returns a 2D plot of vectors that have been dimensionally reduced.

        Args:
            collection:
                A collection or the name of a collection
            point_label:
                The label of every point. This should be found in the document.
            dim_reduction_field:
                The dimensionally-reduced vectors.
            cluster_field:
                The field by which it is clustered.
            cluster_label:
                The name of the clusters
            include_centroids:
                Whether to include the centroids of every cluster
        
        Returns:
            Plotly figure object
        
        See example from: https://colab.research.google.com/drive/10u7b3lkIVJ-lceCmr34ywscOGueIFd0I?usp=sharing
        
        Example:
            >>> collection_name = 'nlp-qa'
            >>> cluster_field = 'question_vector_'
            >>> cluster_label = 'category'
            >>> alias = '1st_cluster'
            >>> dim_reduction_field = '_dr_.default.2.question_vectors_' # the '.' in names implies nested dictionaries in Vi
            >>> vi_client.plot_dimensionality_reduced_vectors(collection=collection_name,
                    cluster_field=cluster_field,
                    cluster_label=cluster_label,
                    point_label='question_title',
                    dim_reduction_field=dim_reduction_field, 
                    include_centroids=True, 
                    alias=alias)
        
        """
        fig = go.Figure()
        if include_centroids:
            if not isinstance(collection, str):
                raise NotImplementedError(
                    "Centroid visualisation not included for custom clustering."
                    + "Please add them to yourself by using add_trace to the returned fig output."
                )

            cluster_centroid_documents = self.advanced_cluster_centroid_documents(
                collection, cluster_field, alias=alias
            )

            fig.add_trace(
                self._scatter_plot_centroids(
                    cluster_centroid_documents=cluster_centroid_documents,
                    dim_reduction_field=dim_reduction_field,
                    point_label=point_label,
                    mode=mode
                )
            )

        # If collection is simply a name, retrieve collection
        if isinstance(collection, str):
            fields_to_include = [point_label, dim_reduction_field, cluster_field, cluster_label]
            fields_to_include = [x for x in fields_to_include if x is not None]
            collection = self.retrieve_all_documents(collection, include_fields=[fields_to_include])

        if cluster_label is None:
            color_dict = None
        else:
            cluster_titles = [
                self.get_field(cluster_label, x) for x in collection
            ]
            cluster_titles = list(set(cluster_titles))
            cluster_titles_color_map = dict(enumerate(cluster_titles))
            color_dict = {v: k + 5 for k, v in cluster_titles_color_map.items()}
        
        if cluster_label is None:
            fig.add_trace(
                self._scatter_plot_documents(
                    filtered_collection=collection,
                    dim_reduction_field=dim_reduction_field,
                    color=color,
                    point_label=point_label,
                    mode=mode
                )
            )
        else:
            for title in tqdm(cluster_titles):
                filtered_collection = [
                    x
                    for x in collection
                    if self.get_field(cluster_label, x) == title
                ]
                fig.add_trace(
                    self._scatter_plot_documents(
                        title=title,
                        filtered_collection=filtered_collection,
                        dim_reduction_field=dim_reduction_field,
                        color=color_dict[title],
                        point_label=point_label,
                    )
                )
            fig.update_layout(showlegend=True)
        return fig

    def plot_1d_cosine_similarity(
        self,
        documents: list,
        vector_fields: List[str],
        label: str,
        anchor_document: dict = None,
        anchor_index: Union[str, int] = 0,
        orientation="h",
        barmode="group",
    ):
        """
        Compare 1 document against other documents.
        Ensure that the name is unique, otherwise the plot will simply take the mean.
        
        Args:
            documents: list of documents (dictionaries) to feed in
            vector_fields: vector field to calculate cosine similarity on 
            label: the x label for the bar plot 
            anchor_document: the document to compare it on
            anchor_index: the anchor index to compare it on
            orientation: The orientation of the bar chart
        
        Returns:
            Plotly Figure: returns a horizontal barplot showing cosine similarity scores.
        
        Example:
            >>> cluster_field = 'question_vector_'
            >>> cluster_label = 'category'
            >>> alias = '1st_cluster'
            >>> dim_reduction_field = '_dr_.default.2.question_vectors_' # the '.' in names implies nested dictionaries in Vi
            >>> vi_client.plot_1d_cosine_similarity(collection=collection_name,
                    cluster_field=cluster_field,
                    cluster_label=cluster_label,
                    point_label='question_title',
                    dim_reduction_field=dim_reduction_field, 
                    include_centroids=True, 
                    alias=alias)
        
        """
        fig = go.Figure()
        if isinstance(vector_fields, str):
            vector_fields = [vector_fields]
        if anchor_document is None:
            other_documents = copy.deepcopy(documents)
            if isinstance(anchor_index, int):
                anchor_document = other_documents.pop(anchor_index)
            elif isinstance(anchor_index, str):
                # Loop through list to get ID
                for i, doc in enumerate(other_documents):
                    if anchor_index == doc["_id"]:
                        anchor_document = other_documents.pop(i)
                        break
        for vector_field in vector_fields:
            fig.add_trace(self._plot_1d_cosine_similarity_for_1_vector_field(
                documents=documents,
                vector_field=vector_field,
                label=label,
                anchor_document=anchor_document, 
                anchor_index=anchor_index,
                orientation=orientation))
        fig.update_layout(
            barmode='group', 
            title=f"Comparing with {anchor_document[label]}"
        )
        return fig
    
    def _plot_1d_cosine_similarity_for_1_vector_field(self, 
        documents: list,
        vector_field: str,
        label: str,
        anchor_document: dict=None,
        anchor_index: Union[str, int]=0,
        orientation="h") -> go.Bar:
            """
            Compare 1 document against other documents.

            Args:
                documents: list of documents (dictionaries) to feed in
                vector_fields: vector field to calculate cosine similarity on 
                label: the x label for the bar plot 
                anchor_document: the document to compare it on
                anchor_index: the anchor index to compare it on
                orientation: The orientation of the bar chart
            Returns:
                None, returns a horizontal barplot showing cosine similarity scores.

            Example:
                >>> cluster_field = 'question_vector_'
                >>> cluster_label = 'category'
                >>> alias = '1st_cluster'
                >>> dim_reduction_field = '_dr_.default.2.question_vectors_' # the '.' in names implies nested dictionaries in Vi
                >>> vi_client.plot_1d_cosine_similarity(collection=collection_name,
                        cluster_field=cluster_field,
                        cluster_label=cluster_label,
                        point_label='question_title',
                        dim_reduction_field=dim_reduction_field, 
                        include_centroids=True, 
                        alias=alias)
            
            """
            
            try:
                scores = self.get_cosine_similarity_scores(
                    documents, anchor_document, vector_field=vector_field
                )
            except NameError:
                raise APIError(f"Anchor document with {anchor_index} not found.")

            for i, doc in enumerate(documents):
                doc["cos_score"] = scores[i]

            mean_dict = MeanDict()
            for i, doc in enumerate(documents):
                mean_dict[doc[label]] = doc["cos_score"]
            
            x, y = mean_dict.get_x_y()

            return go.Bar(
                x=y,
                y=x,
                orientation=orientation,
                name=vector_field
            )
        
    def plot_2d_cosine_similarity(
        self,
        documents: List[Dict[str, Any]],
        anchor_documents: List[Dict[str, Any]],
        vector_fields: Union[str, List[str]],
        label: str,
        mode: str='markers+text'
    ):
        """
        Plot cosine similarity with 2 anchor documents to compare with against other documents.

        Args:
            documents: list of documents (dictionaries) to feed in
            vector_field: vector field to calculate cosine similarity on 
            label: the x label for the bar plot 
            anchor_document: the document to compare it on
            anchor_index: the anchor index to compare it on
        Returns:
            A scatterplot showing cosine similarity scores with each axes being a specific document.
        
        Example:
            >>> cluster_field = 'question_vector_'
            >>> cluster_label = 'category'
            >>> alias = '1st_cluster'
            >>> dim_reduction_field = '_dr_.default.2.question_vectors_' # the '.' in names implies nested dictionaries in Vi
            >>> vi_client.plot_2d_cosine_similarity(documents=documents[2:],
                    anchor_documents=documents[:2],
                    vector_fields=vector_field,
                    label=label
                    )

        """
        assert (
            len(anchor_documents) == 2
        ), "You need 2 anchor documents for a 2d cosine similarity plot."
        fig = go.Figure()
        if isinstance(vector_fields, str):
            vector_fields = [vector_fields]
        for vector_field in vector_fields:
            
            scores_x = self.get_cosine_similarity_scores(
                documents, anchor_documents[0], vector_field
            )
            scores_y = self.get_cosine_similarity_scores(
                documents, anchor_documents[1], vector_field
            )

            for i, doc in enumerate(documents):
                doc["cos_score_x"] = scores_x[i]
                doc["cos_score_y"] = scores_y[i]

            x = [round(x["cos_score_x"], 3) for x in documents]
            y = [round(x["cos_score_y"], 3) for x in documents]
            labels = [x[label] for x in documents]
            fig.add_trace(go.Scatter(x=x, y=y, text=labels, mode=mode, name=vector_field))
        fig.update_xaxes(title_text=f"Comparing with {anchor_documents[0][label]}")
        fig.update_yaxes(title_text=f"Comparing with {anchor_documents[1][label]}")
        fig.update_layout(
            title_text=f"2D Cosine Similarity Comparison With {anchor_documents[0][label]} and {anchor_documents[1][label]}"
        )
        return fig
